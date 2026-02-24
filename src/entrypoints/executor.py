from loguru import logger

from src.application.order_mapper import map_order_to_everstox
from src.domain.everstox_order import EverstoxOrder
from src.domain.interfaces import IEverstoxService, IOrderService, IReportService
from src.domain.order import Order


class Executor:
    """Fetches paid, unfulfilled Shopify orders and forwards them to Everstox."""

    def __init__(
        self,
        order_service: IOrderService,
        everstox_service: IEverstoxService,
        report_service: IReportService,
    ) -> None:
        self._order_service = order_service
        self._everstox_service = everstox_service
        self._report_service = report_service

    def run(self, days: int = 14) -> None:
        logger.info(f"Fetching paid, unfulfilled orders from the last {days} days…")
        orders: list[Order] = self._order_service.get_unfulfilled_paid_orders(days=days)
        logger.info(f"Found {len(orders)} order(s) — forwarding to Everstox.")

        for order in orders:
            logger.debug(
                f"{order.name} | {order.financial_status} | {order.fulfillment_status} |  {order.line_items} | {order.tags}"
                f"| {order.total_price} {order.currency}"
            )

        # Map and send; collect pairs for the report
        sent: list[tuple[Order, EverstoxOrder]] = []
        for order in orders:
            everstox_order = map_order_to_everstox(order)
            self._everstox_service.send_order(everstox_order)
            sent.append((order, everstox_order))

        report_path = self._report_service.generate(orders, sent)
        logger.info(f"Done. Report written to: {report_path}")
