from typing import Protocol

from .everstox_order import EverstoxOrder
from .order import Order


class IOrderService(Protocol):
    def get_unfulfilled_paid_orders(self, days: int = 14) -> list[Order]: ...


class IEverstoxService(Protocol):
    def send_order(self, order: EverstoxOrder) -> dict: ...


class IReportService(Protocol):
    def generate(
        self,
        orders: list[Order],
        pairs: list[tuple[Order, EverstoxOrder]],
    ) -> str:
        """Generate the report and return the output path."""
        ...
