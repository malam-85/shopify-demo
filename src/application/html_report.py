"""Generates an HTML run report listing loaded Shopify orders and Everstox payloads."""

import html
import json
from datetime import UTC, datetime

from src.domain.everstox_order import EverstoxOrder
from src.domain.order import Order

_CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #f4f6f9; color: #1a1a2e; padding: 2rem; }
  h1 { font-size: 1.6rem; margin-bottom: 0.25rem; }
  .meta { color: #666; font-size: 0.85rem; margin-bottom: 2rem; }
  h2 { font-size: 1.1rem; margin-bottom: 0.75rem; color: #444; }

  .cards { display: flex; gap: 1rem; margin-bottom: 2rem; }
  .card { background: #fff; border-radius: 8px; padding: 1.25rem 1.75rem;
          box-shadow: 0 1px 4px rgba(0,0,0,.08); min-width: 140px; }
  .card .value { font-size: 2rem; font-weight: 700; color: #4f46e5; }
  .card .label { font-size: 0.8rem; color: #888; margin-top: 0.2rem; }

  table { width: 100%; border-collapse: collapse; background: #fff;
          border-radius: 8px; overflow: hidden;
          box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 2rem; }
  th { background: #4f46e5; color: #fff; text-align: left;
       padding: 0.65rem 1rem; font-size: 0.8rem; text-transform: uppercase;
       letter-spacing: .04em; }
  td { padding: 0.6rem 1rem; font-size: 0.88rem; border-bottom: 1px solid #f0f0f0; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #f9f9ff; }

  .badge { display: inline-block; padding: 2px 8px; border-radius: 99px;
           font-size: 0.75rem; font-weight: 600; }
  .badge-paid   { background: #d1fae5; color: #065f46; }
  .badge-unfulfilled { background: #fee2e2; color: #991b1b; }
  .badge-partial { background: #fef3c7; color: #92400e; }

  details { background: #fff; border-radius: 8px;
            box-shadow: 0 1px 4px rgba(0,0,0,.08);
            margin-bottom: 0.75rem; overflow: hidden; }
  summary { cursor: pointer; padding: 0.75rem 1rem;
            font-size: 0.9rem; font-weight: 600;
            display: flex; align-items: center; gap: 0.5rem;
            list-style: none; user-select: none; }
  summary::-webkit-details-marker { display: none; }
  summary::before { content: "▶"; font-size: 0.7rem; color: #4f46e5;
                    transition: transform .15s; display: inline-block; }
  details[open] summary::before { transform: rotate(90deg); }
  summary:hover { background: #f9f9ff; }
  .order-num { color: #4f46e5; }
  pre { padding: 1rem 1.25rem; font-size: 0.78rem; overflow-x: auto;
        background: #1e1e2e; color: #cdd6f4; line-height: 1.5; }
"""


def _badge(text: str | None, kind: str) -> str:
    if not text:
        return "<span style='color:#aaa'>—</span>"
    cls = (
        f"badge-{text.lower()}"
        if f"badge-{text.lower()}"
        in ("badge-paid", "badge-unfulfilled", "badge-partial")
        else "badge"
    )
    return f'<span class="badge {cls}">{html.escape(text)}</span>'


def _orders_table(orders: list[Order]) -> str:
    rows = "".join(
        f"""<tr>
          <td><strong>{html.escape(o.name)}</strong></td>
          <td>{_badge(o.financial_status, "paid")}</td>
          <td>{_badge(o.fulfillment_status, "unfulfilled")}</td>
          <td>{html.escape(o.total_price)} {html.escape(o.currency)}</td>
          <td>{html.escape(str(o.created_at))}</td>
        </tr>"""
        for o in orders
    )
    return f"""
    <table>
      <thead><tr>
        <th>Order</th><th>Financial Status</th>
        <th>Fulfillment Status</th><th>Total</th><th>Created At</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


def _everstox_details(pairs: list[tuple[Order, EverstoxOrder]]) -> str:
    blocks = []
    for shopify_order, everstox_order in pairs:
        payload = json.dumps(
            everstox_order.model_dump(mode="json", exclude_none=True),
            indent=2,
            ensure_ascii=False,
        )
        blocks.append(f"""
        <details>
          <summary>
            <span class="order-num">{html.escape(shopify_order.name)}</span>
            &nbsp;·&nbsp;{html.escape(everstox_order.order_number)}
            &nbsp;·&nbsp;{html.escape(shopify_order.financial_status)}
          </summary>
          <pre>{html.escape(payload)}</pre>
        </details>""")
    return "\n".join(blocks)


def build_html_report(
    orders: list[Order], pairs: list[tuple[Order, EverstoxOrder]]
) -> str:
    """Return a complete HTML report page as a string.

    Args:
        orders: All Shopify orders that were loaded.
        pairs:  (shopify_order, everstox_order) for every order that was sent.
    """
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Shopify → Everstox Report</title>
  <style>{_CSS}</style>
</head>
<body>
  <h1>Shopify → Everstox Report</h1>
  <p class="meta">Generated at {generated_at}</p>

  <div class="cards">
    <div class="card">
      <div class="value">{len(orders)}</div>
      <div class="label">Orders loaded</div>
    </div>
    <div class="card">
      <div class="value">{len(pairs)}</div>
      <div class="label">Sent to Everstox</div>
    </div>
  </div>

  <h2>Loaded Orders</h2>
  {_orders_table(orders)}

  <h2>Everstox Payloads</h2>
  {_everstox_details(pairs)}
</body>
</html>"""


class HtmlReportService:
    """Writes a timestamped HTML report and returns the file path."""

    def generate(
        self,
        orders: list[Order],
        pairs: list[tuple[Order, EverstoxOrder]],
    ) -> str:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
        path = f"report_{timestamp}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_html_report(orders, pairs))
        return path
