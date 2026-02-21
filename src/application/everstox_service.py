import httpx
from loguru import logger

from src.domain.everstox_order import EverstoxOrder
from src.shared.decorators import log_errors


class EverstoxAPIError(Exception):
    """Raised when the Everstox API returns a non-2xx response."""


class EverstoxService:
    """Sends orders to the Everstox fulfillment platform."""

    CREATE_ORDER_PATH = "/fulfillment/api/v1/orders/"

    def __init__(self, client: httpx.Client, base_url: str, api_key: str) -> None:
        self._client = client
        self._endpoint = base_url.rstrip("/") + self.CREATE_ORDER_PATH
        self._headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        }

    @log_errors
    def send_order(self, order: EverstoxOrder) -> dict:
        """POST ``order`` to the Everstox create-order endpoint.

        Returns the parsed JSON response body on success.
        Raises:
            EverstoxAPIError: on non-2xx HTTP responses.
        """
        payload = order.model_dump(mode="json", exclude_none=True)

        response = self._client.post(
            self._endpoint, headers=self._headers, json=payload
        )

        if not response.is_success:
            raise EverstoxAPIError(
                f"Everstox API error {response.status_code}: {response.text}"
            )

        logger.info(
            f"[Everstox] Order {order.order_number} accepted — {response.status_code}"
        )
        return response.json()
