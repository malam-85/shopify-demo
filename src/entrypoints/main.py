import httpx
from loguru import logger

from src.application.everstox_service import EverstoxService
from src.application.html_report import HtmlReportService
from src.application.order_service import OrderService
from src.entrypoints.executor import Executor
from src.entrypoints.settings import config
from src.infrastructure.order_repository import OrderRepository
from src.infrastructure.shopify_client import ShopifyGraphQLClient

FETCH_DAYS = 14


def _mock_everstox_handler(request: httpx.Request) -> httpx.Response:
    """Mock transport handler — logs what would be sent and returns a 201."""
    logger.info(f"[Everstox] MOCK POST {request.url}\n{request.content.decode()}")
    return httpx.Response(201, json={"status": "accepted"})


def main() -> None:
    # --- Shopify layer ---
    shopify_client = ShopifyGraphQLClient(
        shop_name=config.SHOPIFY_SHOP_NAME,
        access_token=config.SHOPIFY_ACCESS_TOKEN,
        api_version=config.SHOPIFY_API_VERSION,
    )
    order_service = OrderService(OrderRepository(shopify_client))

    # --- Everstox layer ---
    # To go live: replace MockTransport with httpx.Client() (no transport arg).
    http_client = httpx.Client(transport=httpx.MockTransport(_mock_everstox_handler))
    everstox_service = EverstoxService(
        client=http_client,
        base_url=config.EVERSTOX_BASE_URL,
        api_key=config.EVERSTOX_API_KEY,
    )

    # --- Run pipeline ---
    executor = Executor(
        order_service=order_service,
        everstox_service=everstox_service,
        report_service=HtmlReportService(),
    )
    executor.run(days=FETCH_DAYS)


if __name__ == "__main__":
    main()
