"""Tests for OrderRepository.fetch_orders using a mocked GraphQL client."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.domain.order import Order
from src.infrastructure.order_repository import OrderRepository
from src.infrastructure.shopify_client import ShopifyGraphQLClient, ShopifyGraphQLError


def _make_node(order_id: str = "gid://shopify/Order/1", name: str = "#1001") -> dict:
    """Helper: build a minimal GraphQL order node."""
    return {
        "id": order_id,
        "name": name,
        "createdAt": "2025-02-01T10:00:00Z",
        "displayFinancialStatus": "PAID",
        "displayFulfillmentStatus": "UNFULFILLED",
        "totalPriceSet": {"shopMoney": {"amount": "99.99", "currencyCode": "EUR"}},
    }


def _single_page_response(nodes: list[dict]) -> dict:
    """Wrap nodes in a single-page orders GraphQL response."""
    return {
        "orders": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "edges": [{"node": n} for n in nodes],
        }
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_fetch_orders_returns_orders() -> None:
    """Two matching orders are returned and correctly mapped to domain objects."""
    client = MagicMock(spec=ShopifyGraphQLClient)
    client.execute.return_value = _single_page_response(
        [_make_node("gid://shopify/Order/1", "#1001"), _make_node("gid://shopify/Order/2", "#1002")]
    )

    repo = OrderRepository(client)
    orders = repo.fetch_orders(days=14)

    assert len(orders) == 2
    assert all(isinstance(o, Order) for o in orders)
    assert orders[0].name == "#1001"
    assert orders[1].name == "#1002"
    assert orders[0].financial_status == "PAID"
    assert orders[0].total_price == "99.99"
    assert orders[0].currency == "EUR"


# ---------------------------------------------------------------------------
# Edge case: empty result
# ---------------------------------------------------------------------------


def test_fetch_orders_empty_response() -> None:
    """An empty edges list returns an empty list without error."""
    client = MagicMock(spec=ShopifyGraphQLClient)
    client.execute.return_value = _single_page_response([])

    repo = OrderRepository(client)
    orders = repo.fetch_orders(days=14)

    assert orders == []
    client.execute.assert_called_once()


# ---------------------------------------------------------------------------
# Edge case: days=0 (today only)
# ---------------------------------------------------------------------------


def test_fetch_orders_days_zero_uses_todays_date() -> None:
    """days=0 computes a since-date of today and passes it in the query string."""
    client = MagicMock(spec=ShopifyGraphQLClient)
    client.execute.return_value = _single_page_response([])

    with patch("src.infrastructure.order_repository.datetime") as mock_dt:
        fixed_now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
        mock_dt.now.return_value = fixed_now
        # timedelta still needs to work normally
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        repo = OrderRepository(client)
        repo.fetch_orders(days=0)

    _, kwargs = client.execute.call_args
    variables: dict = kwargs.get("variables") or client.execute.call_args[0][1]
    assert "2025-06-15T12:00:00Z" in variables["query"]


# ---------------------------------------------------------------------------
# Edge case: API returns GraphQL errors
# ---------------------------------------------------------------------------


def test_fetch_orders_raises_on_graphql_errors() -> None:
    """ShopifyGraphQLError from the client propagates out of the repository."""
    client = MagicMock(spec=ShopifyGraphQLClient)
    client.execute.side_effect = ShopifyGraphQLError([{"message": "Access denied"}])

    repo = OrderRepository(client)

    with pytest.raises(ShopifyGraphQLError):
        repo.fetch_orders(days=14)


# ---------------------------------------------------------------------------
# Edge case: pagination (two pages)
# ---------------------------------------------------------------------------


def test_fetch_orders_paginates_correctly() -> None:
    """Repository follows pagination cursors and merges results from both pages."""
    client = MagicMock(spec=ShopifyGraphQLClient)

    page1 = {
        "orders": {
            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-abc"},
            "edges": [{"node": _make_node("gid://shopify/Order/1", "#1001")}],
        }
    }
    page2 = {
        "orders": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "edges": [{"node": _make_node("gid://shopify/Order/2", "#1002")}],
        }
    }
    client.execute.side_effect = [page1, page2]

    repo = OrderRepository(client)
    orders = repo.fetch_orders(days=14)

    assert len(orders) == 2
    assert client.execute.call_count == 2
    # Second call must carry the cursor from page 1
    second_variables: dict = client.execute.call_args_list[1][0][1]
    assert second_variables["after"] == "cursor-abc"
