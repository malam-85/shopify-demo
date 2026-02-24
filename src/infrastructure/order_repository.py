from datetime import UTC, datetime, timedelta
from loguru import logger
from src.domain.order import (
    Order,
    OrderLineItem,
    OrderBillingAddress,
    OrderShippingAddress,
    OrderShippingLine,
    OrderTaxLine,
)
from src.infrastructure.shopify_client import ShopifyGraphQLClient
import time


class OrderRepository:
    # Fetch 50 orders per page (Shopify max is 250, 50 is a safe default)
    PAGE_SIZE = 50

    BLACKLIST: set[str] = set()
    WHITELIST: set[str] = set()

    COST_BUFFER = 50

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
                  tags
                  email
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
                  shippingLine {
                    title
                    code
                    originalPriceSet   { shopMoney { amount currencyCode } }
                    discountedPriceSet { shopMoney { amount currencyCode } }
                    taxLines {
                      rate
                      priceSet { shopMoney { amount currencyCode } }
                    }
                  }
                lineItems(first: 50) {
                    edges {
                        node {
                            id
                            title
                            quantity
                            unfulfilledQuantity
                            sku
                            originalUnitPriceSet {
                                shopMoney { amount currencyCode }
                            }
                            taxLines {
                                rate
                                priceSet {
                                    shopMoney { amount currencyCode }
                                }
                            }
                            discountAllocations {
                                allocatedAmountSet { shopMoney { amount currencyCode } }
                            }
                            customAttributes { key value }
                        }
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
            # Log cost info
            cost = data.get("extensions", {}).get("cost", {})
            throttle = cost.get("throttleStatus", {})
            actual_cost = cost.get("actualQueryCost", 0)
            currently_available = throttle.get("currentlyAvailable", 1000)
            logger.debug(
                f"Query cost: {actual_cost} | "
                f"Available: {currently_available} / {throttle.get('maximumAvailable')}"
            )

            restore_rate = throttle.get("restoreRate", 50)

            # Only wait if available budget is less than next expected query cost + buffer
            # Example:
            # actual_cost = 10
            # currently_available = 50
            # BUFFER = 50
            # 50 < (10 + 50) → 50 < 60 → warte
            # points_needed = 60 - 50 = 10
            # wait_seconds = 10 / 50 = 0.2s

            if currently_available < actual_cost + self.COST_BUFFER:
                points_needed = (actual_cost + self.COST_BUFFER) - currently_available
                wait_seconds = points_needed / restore_rate
                logger.warning(
                    f"Budget low — available: {currently_available}, "
                    f"next query needs: {actual_cost + self.COST_BUFFER} — waiting {wait_seconds:.1f}s"
                )
                time.sleep(wait_seconds)

            page = data["data"]["orders"]

            for edge in page["edges"]:
                node = edge["node"]
                # normalize to lowercase
                order_tags = [tag.lower() for tag in node.get("tags", [])]

                # Blacklist check — blacklist always wins (precedence decision)
                if any(tag in self.BLACKLIST for tag in order_tags):
                    matched = [tag for tag in order_tags if tag in self.BLACKLIST]
                    logger.info(
                        f"Order {node['name']} excluded — blacklist tag: {matched}"
                    )
                    continue

                # Whitelist check — if whitelist is defined, order must have at least one match
                if self.WHITELIST and not any(
                    tag in self.WHITELIST for tag in order_tags
                ):
                    logger.info(
                        f"Order {node['name']} excluded — no whitelist tag found"
                    )
                    continue

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

        line_items = [
            OrderLineItem(
                id=item["node"]["id"],
                title=item["node"]["title"],
                quantity=item["node"]["unfulfilledQuantity"],
                sku=item["node"].get("sku"),
                price=float(
                    item["node"]["originalUnitPriceSet"]["shopMoney"]["amount"]
                ),
                currency=item["node"]["originalUnitPriceSet"]["shopMoney"][
                    "currencyCode"
                ],
                tax_lines=[
                    OrderTaxLine(
                        rate=float(t["rate"]),
                        amount=float(t["priceSet"]["shopMoney"]["amount"]),
                        currency=t["priceSet"]["shopMoney"]["currencyCode"],
                    )
                    for t in item["node"].get("taxLines", [])
                ],
                discount_total=sum(
                    float(d["allocatedAmountSet"]["shopMoney"]["amount"])
                    for d in item["node"].get("discountAllocations", [])
                ),
                custom_attributes=item["node"].get("customAttributes", []),
            )
            for item in node["lineItems"]["edges"]
            if item["node"]["unfulfilledQuantity"] > 0
        ]

        shipping_line: OrderShippingLine | None = None
        if raw_sl := node.get("shippingLine"):
            sl_orig = raw_sl["originalPriceSet"]["shopMoney"]
            sl_disc = raw_sl["discountedPriceSet"]["shopMoney"]
            shipping_line = OrderShippingLine(
                title=raw_sl.get("title"),
                code=raw_sl.get("code"),
                original_price=float(sl_orig["amount"]),
                discounted_price=float(sl_disc["amount"]),
                currency=sl_orig["currencyCode"],
                tax_lines=[
                    OrderTaxLine(
                        rate=float(t["rate"]),
                        amount=float(t["priceSet"]["shopMoney"]["amount"]),
                        currency=t["priceSet"]["shopMoney"]["currencyCode"],
                    )
                    for t in raw_sl.get("taxLines", [])
                ],
            )

        return Order(
            id=node["id"],
            name=node["name"],
            created_at=node["createdAt"],
            financial_status=node["displayFinancialStatus"],
            fulfillment_status=node.get("displayFulfillmentStatus"),
            total_price=money["amount"],
            currency=money["currencyCode"],
            tags=node.get("tags", []),
            email=node.get("email"),
            shipping_address=shipping_address,
            billing_address=billing_address,
            shipping_line=shipping_line,
            line_items=line_items,
        )
