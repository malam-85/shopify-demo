from src.domain.order import Order
from src.infrastructure.order_repository import OrderRepository


class OrderService:
    """Application service for order-related operations."""

    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    def get_unfulfilled_paid_orders(self, days: int = 14) -> list[Order]:
        """Return paid, not-yet-fully-fulfilled orders from the last ``days`` days."""
        return self._repository.fetch_orders(days)
