from datetime import UTC, datetime, timedelta

from src.domain.order import Order, OrderBillingAddress, OrderShippingAddress
from src.infrastructure.shopify_client import ShopifyGraphQLClient


class OrderRepository:
    # Fetch 50 orders per page (Shopify max is 250, 50 is a safe default)
    PAGE_SIZE = 50

    """Fetches orders from the Shopify Admin GraphQL API."""

    def __init__(self, client: ShopifyGraphQLClient) -> None:
        self._client = client

    def fetch_orders(self, days: int = 14) -> list[Order]:
        """Return paid, not-yet-fully-fulfilled orders created in the last ``days`` days.

        Filters applied via Shopify query string:
        - financial_status:paid
        - fulfillment_status:unshipped OR fulfillment_status:partial
        - created_at >= <days ago>
        """
        since: datetime = datetime.now(UTC) - timedelta(days=days)
        since_iso: str = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Shopify search query: paid and not fully fulfilled within date range
        query_string = (
            f"financial_status:paid "
            f"fulfillment_status:unshipped OR fulfillment_status:partial "
            f"created_at:>={since_iso}"
        )

        orders: list[Order] = []
        cursor: str | None = None

        orders_query = """
          query FetchOrders($query: String!, $first: Int!, $after: String) {
            orders(query: $query, first: $first, after: $after) {
              pageInfo {
                hasNextPage
                endCursor
              }
              edges {
                node {
                  id
                  name
                  createdAt
                  displayFinancialStatus
                  displayFulfillmentStatus
                shippingAddress {
                    firstName
                    lastName
                    address1
                    address2
                    city
                    province
                    countryCode
                    zip
                    phone
                }                  
                  billingAddress {
                      firstName
                      lastName
                      address1
                      address2
                      city
                      province
                      provinceCode
                      country
                      countryCode
                      zip
                      phone
                      company
                  }
                  totalPriceSet {
                    shopMoney {
                      amount
                      currencyCode
                    }
                  }
                }
              }
            }
          }
          """

        # Paginate until all matching orders are fetched
        while True:
            variables: dict = {
                "query": query_string,
                "first": self.PAGE_SIZE,
                "after": cursor,
            }
            data = self._client.execute(orders_query, variables)
            page = data["orders"]

            for edge in page["edges"]:
                orders.append(self._map(edge["node"]))

            page_info = page["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]

        return orders

    @staticmethod
    def _map(node: dict) -> Order:
        """Map a raw GraphQL node to an ``Order`` domain object."""
        money = node["totalPriceSet"]["shopMoney"]

        shipping_address: OrderShippingAddress | None = None
        if raw := node.get("shippingAddress"):
            shipping_address = OrderShippingAddress(
                first_name=raw["firstName"],
                last_name=raw["lastName"],
                country_code=raw["countryCode"],
                city=raw["city"],
                zip=raw["zip"],
                address_1=raw["address1"],
                address_2=raw.get("address2"),
                phone=raw.get("phone"),
                province=raw.get("province"),
            )

        billing_address: OrderBillingAddress | None = None
        if raw := node.get("billingAddress"):
            billing_address = OrderBillingAddress(
                first_name=raw["firstName"],
                last_name=raw["lastName"],
                country_code=raw["countryCode"],
                city=raw["city"],
                zip=raw["zip"],
                address_1=raw["address1"],
                address_2=raw.get("address2"),
                company=raw.get("company"),
                phone=raw.get("phone"),
                country=raw.get("country"),
                province=raw.get("province"),
                province_code=raw.get("provinceCode"),
            )

        return Order(
            id=node["id"],
            name=node["name"],
            created_at=node["createdAt"],
            financial_status=node["displayFinancialStatus"],
            fulfillment_status=node.get("displayFulfillmentStatus"),
            total_price=money["amount"],
            currency=money["currencyCode"],
            shipping_address=shipping_address,
            billing_address=billing_address,
        )
