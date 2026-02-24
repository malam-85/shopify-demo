"""Tests for OrderRepository.fetch_orders using a mocked GraphQL client."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.domain.order import Order, OrderLineItem, OrderShippingLine, OrderTaxLine
from src.infrastructure.order_repository import OrderRepository
from src.infrastructure.shopify_client import ShopifyGraphQLClient, ShopifyGraphQLError
from src.application.order_mapper import map_order_to_everstox


def _make_node(order_id: str = "gid://shopify/Order/1", name: str = "#1001") -> dict:
    """Helper: build a minimal GraphQL order node."""
    return {
        "id": order_id,
        "name": name,
        "createdAt": "2025-02-01T10:00:00Z",
        "displayFinancialStatus": "PAID",
        "displayFulfillmentStatus": "UNFULFILLED",
        "tags": [],
        "email": "customer@example.com",
        "totalPriceSet": {"shopMoney": {"amount": "99.99", "currencyCode": "EUR"}},
        "shippingLine": {
            "title": "Standard Shipping",
            "code": "standard",
            "originalPriceSet":   {"shopMoney": {"amount": "5.00", "currencyCode": "EUR"}},
            "discountedPriceSet": {"shopMoney": {"amount": "5.00", "currencyCode": "EUR"}},
            "taxLines": [],
        },
        "lineItems": {"edges": []},
    }


def _make_line_item_node(
    item_id: str = "gid://shopify/LineItem/1",
    sku: str = "SKU-001",
    quantity: int = 2,
    price: str = "10.00",
    currency: str = "EUR",
    tax_rate: float = 0.19,
    tax_amount: str = "1.90",
    discount: str = "0.00",
) -> dict:
    """Helper: build a GraphQL line item node."""
    return {
        "id": item_id,
        "title": "Test Product",
        "quantity": quantity,
        "unfulfilledQuantity": quantity,
        "sku": sku,
        "originalUnitPriceSet": {"shopMoney": {"amount": price, "currencyCode": currency}},
        "taxLines": [
            {
                "rate": str(tax_rate),
                "priceSet": {"shopMoney": {"amount": tax_amount, "currencyCode": currency}},
            }
        ],
        "discountAllocations": [
            {"allocatedAmountSet": {"shopMoney": {"amount": discount, "currencyCode": currency}}}
        ] if float(discount) > 0 else [],
        "customAttributes": [],
    }


def _single_page_response(nodes: list[dict]) -> dict:
    """Wrap nodes in a single-page orders GraphQL response."""
    return {
        "data": {
            "orders": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "edges": [{"node": n} for n in nodes],
            }
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
        "data": {"orders": {
            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-abc"},
            "edges": [{"node": _make_node("gid://shopify/Order/1", "#1001")}],
        }}
    }
    page2 = {
        "data": {"orders": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "edges": [{"node": _make_node("gid://shopify/Order/2", "#1002")}],
        }}
    }
    client.execute.side_effect = [page1, page2]

    repo = OrderRepository(client)
    orders = repo.fetch_orders(days=14)

    assert len(orders) == 2
    assert client.execute.call_count == 2
    # Second call must carry the cursor from page 1
    second_variables: dict = client.execute.call_args_list[1][0][1]
    assert second_variables["after"] == "cursor-abc"


# ---------------------------------------------------------------------------
# Repository: new field mapping
# ---------------------------------------------------------------------------


def test_fetch_orders_maps_email_and_shipping_line() -> None:
    """email and shippingLine are mapped into the Order domain object."""
    node = _make_node()
    node["shippingLine"]["taxLines"] = [
        {"rate": "0.19", "priceSet": {"shopMoney": {"amount": "0.95", "currencyCode": "EUR"}}}
    ]
    client = MagicMock(spec=ShopifyGraphQLClient)
    client.execute.return_value = _single_page_response([node])

    orders = OrderRepository(client).fetch_orders()

    order = orders[0]
    assert order.email == "customer@example.com"
    assert order.shipping_line is not None
    assert order.shipping_line.title == "Standard Shipping"
    assert order.shipping_line.original_price == 5.0
    assert len(order.shipping_line.tax_lines) == 1
    assert order.shipping_line.tax_lines[0].rate == 0.19


def test_fetch_orders_maps_line_item_tax_and_discount() -> None:
    """taxLines and discountAllocations are mapped into OrderLineItem."""
    node = _make_node()
    node["lineItems"] = {
        "edges": [{"node": _make_line_item_node(discount="2.00")}]
    }
    client = MagicMock(spec=ShopifyGraphQLClient)
    client.execute.return_value = _single_page_response([node])

    orders = OrderRepository(client).fetch_orders()

    item = orders[0].line_items[0]
    assert isinstance(item, OrderLineItem)
    assert item.tax_lines[0].rate == 0.19
    assert item.tax_lines[0].amount == 1.90
    assert item.discount_total == 2.00


def test_fetch_orders_maps_custom_attributes() -> None:
    """customAttributes on line items are passed through to the domain model."""
    node = _make_node()
    line_item = _make_line_item_node()
    line_item["customAttributes"] = [{"key": "gift_message", "value": "Happy Birthday"}]
    node["lineItems"] = {"edges": [{"node": line_item}]}
    client = MagicMock(spec=ShopifyGraphQLClient)
    client.execute.return_value = _single_page_response([node])

    orders = OrderRepository(client).fetch_orders()

    assert orders[0].line_items[0].custom_attributes == [
        {"key": "gift_message", "value": "Happy Birthday"}
    ]


# ---------------------------------------------------------------------------
# Mapper tests
# ---------------------------------------------------------------------------


def _make_order(**kwargs) -> Order:
    """Build a minimal Order domain object for mapper tests."""
    defaults = dict(
        id="gid://shopify/Order/1",
        name="#1001",
        created_at=datetime(2025, 2, 1, 10, 0, 0, tzinfo=UTC),
        financial_status="PAID",
        fulfillment_status="UNFULFILLED",
        total_price="99.99",
        currency="EUR",
        email="customer@example.com",
    )
    return Order(**{**defaults, **kwargs})


def test_mapper_customer_email() -> None:
    """customer_email is taken from order.email."""
    order = _make_order(email="test@shop.com")
    result = map_order_to_everstox(order)
    assert result.customer_email == "test@shop.com"


def test_mapper_customer_email_fallback() -> None:
    """customer_email falls back to unknown@example.com when email is None."""
    order = _make_order(email=None)
    result = map_order_to_everstox(order)
    assert result.customer_email == "unknown@example.com"


def test_mapper_shipping_price_from_shipping_line() -> None:
    """ShippingPrice is populated from Order.shipping_line."""
    sl = OrderShippingLine(
        title="Express",
        original_price=8.00,
        discounted_price=8.00,
        currency="EUR",
        tax_lines=[OrderTaxLine(rate=0.19, amount=1.52, currency="EUR")],
    )
    order = _make_order(shipping_line=sl)
    result = map_order_to_everstox(order)

    sp = result.shipping_price
    assert sp.price == 8.00
    assert sp.tax_amount == 1.52
    assert sp.tax_rate == 0.19
    assert sp.discount == 0.0
    assert sp.price_net_after_discount == pytest.approx(8.00 - 1.52)


def test_mapper_shipping_price_zeros_without_shipping_line() -> None:
    """ShippingPrice defaults to all zeros when no shippingLine is present."""
    order = _make_order(shipping_line=None)
    result = map_order_to_everstox(order)

    sp = result.shipping_price
    assert sp.price == 0.0
    assert sp.tax_amount == 0.0


def test_mapper_shipment_option_propagated_to_all_items() -> None:
    """ShipmentOption from shippingLine.title is set on every OrderItem."""
    sl = OrderShippingLine(
        title="Standard", original_price=5.0, discounted_price=5.0, currency="EUR"
    )
    line_item = OrderLineItem(
        id="1", title="Widget", quantity=1, sku="W-01", price=10.0, currency="EUR"
    )
    order = _make_order(shipping_line=sl, line_items=[line_item])
    result = map_order_to_everstox(order)

    for item in result.order_items:
        assert len(item.shipment_options) == 1
        assert item.shipment_options[0].name == "Standard"


def test_mapper_price_set_per_line_item() -> None:
    """PriceSet is built from line item price, tax, and discount."""
    tax = OrderTaxLine(rate=0.19, amount=1.90, currency="EUR")
    line_item = OrderLineItem(
        id="1", title="Widget", quantity=2, sku="W-01",
        price=10.00, currency="EUR",
        tax_lines=[tax],
        discount_total=2.00,
    )
    order = _make_order(line_items=[line_item])
    result = map_order_to_everstox(order)

    ps = result.order_items[0].price_set[0]
    assert ps.quantity == 2
    assert ps.price == 10.00
    assert ps.tax_amount == 1.90
    assert ps.tax_rate == 0.19
    assert ps.discount == 2.00
    assert ps.price_net_after_discount == pytest.approx(10.00 - 2.00)


def test_mapper_custom_attributes_on_line_item() -> None:
    """customAttributes from line item are mapped to OrderItem.custom_attributes."""
    line_item = OrderLineItem(
        id="1", title="Widget", quantity=1, sku="W-01", price=10.0, currency="EUR",
        custom_attributes=[{"key": "engraving", "value": "Hello"}],
    )
    order = _make_order(line_items=[line_item])
    result = map_order_to_everstox(order)

    ca = result.order_items[0].custom_attributes
    assert len(ca) == 1
    assert ca[0].attribute_key == "engraving"
    assert ca[0].attribute_value == "Hello"
