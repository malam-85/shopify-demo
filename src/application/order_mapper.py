from uuid import UUID

from src.domain.everstox_order import (
    BillingAddress,
    CustomAttribute,
    EverstoxOrder,
    OrderItem,
    PriceSet,
    Product,
    ShipmentOption,
    ShippingAddress,
    ShippingPrice,
)
from src.domain.order import (
    Order,
    OrderBillingAddress,
    OrderLineItem,
    OrderShippingAddress,
)

# Placeholder shop instance ID — replace with the real Everstox shop UUID
_SHOP_INSTANCE_ID = UUID("00000000-0000-0000-0000-000000000000")


def _map_shipping_address(addr: OrderShippingAddress) -> ShippingAddress:
    return ShippingAddress(
        first_name=addr.first_name,
        last_name=addr.last_name,
        country_code=addr.country_code,
        city=addr.city,
        zip=addr.zip,
        address_1=addr.address_1,
        address_2=addr.address_2,
        phone=addr.phone,
        province=addr.province,
    )


def _map_billing_address(addr: OrderBillingAddress) -> BillingAddress:
    return BillingAddress(
        first_name=addr.first_name,
        last_name=addr.last_name,
        country_code=addr.country_code,
        city=addr.city,
        zip=addr.zip,
        address_1=addr.address_1,
        address_2=addr.address_2,
        company=addr.company,
        phone=addr.phone,
        country=addr.country,
        province=addr.province,
        province_code=addr.province_code,
    )


def _map_order_items(
    order_line_items: list[OrderLineItem],
    shipment_options: list[ShipmentOption],
) -> list[OrderItem]:
    return [
        OrderItem(
            quantity=item.quantity,
            product=Product(sku=item.sku),
            shipment_options=shipment_options,
            price_set=[
                PriceSet(
                    quantity=item.quantity,
                    currency=item.currency,
                    price=item.price,
                    price_net_after_discount=item.price - item.discount_total,
                    tax_amount=sum(t.amount for t in item.tax_lines),
                    tax_rate=item.tax_lines[0].rate if item.tax_lines else 0.0,
                    tax=sum(t.amount for t in item.tax_lines),
                    discount=item.discount_total,
                    discount_gross=item.discount_total,
                )
            ],
            custom_attributes=[
                CustomAttribute(
                    attribute_key=ca["key"],
                    attribute_value=ca["value"],
                )
                for ca in item.custom_attributes
            ],
        )
        for item in order_line_items
    ]


def map_order_to_everstox(order: Order) -> EverstoxOrder:
    """Convert a Shopify ``Order`` to an ``EverstoxOrder`` DTO."""
    shipping_address = (
        _map_shipping_address(order.shipping_address)
        if order.shipping_address
        else ShippingAddress(  # fallback: Shopify returned null
            first_name="TODO",
            last_name="TODO",
            country_code="DE",
            city="TODO",
            zip="00000",
            address_1="TODO",
        )
    )
    billing_address = (
        _map_billing_address(order.billing_address)
        if order.billing_address
        else BillingAddress(  # fallback: Shopify returned null
            first_name="TODO",
            last_name="TODO",
            country_code="DE",
            city="TODO",
            zip="00000",
            address_1="TODO",
        )
    )

    sl = order.shipping_line
    shipment_options = [ShipmentOption(name=sl.title)] if sl else []

    shipping_price = ShippingPrice(
        currency=sl.currency if sl else order.currency,
        price=sl.original_price if sl else 0.0,
        price_net_after_discount=(
            sl.discounted_price - sum(t.amount for t in sl.tax_lines)
        )
        if sl
        else 0.0,
        tax_amount=sum(t.amount for t in sl.tax_lines) if sl else 0.0,
        tax_rate=sl.tax_lines[0].rate if (sl and sl.tax_lines) else 0.0,
        tax=sum(t.amount for t in sl.tax_lines) if sl else 0.0,
        discount=(sl.original_price - sl.discounted_price) if sl else 0.0,
        discount_gross=(sl.original_price - sl.discounted_price) if sl else 0.0,
    )

    line_items = (
        _map_order_items(order.line_items, shipment_options)
        if order.line_items
        else [OrderItem(quantity=1, product=Product(sku="TODO"))]
    )

    return EverstoxOrder(
        shop_instance_id=_SHOP_INSTANCE_ID,
        order_number=order.name,
        order_date=order.created_at,
        customer_email=order.email or "unknown@example.com",
        financial_status=order.financial_status,
        shipping_address=shipping_address,
        billing_address=billing_address,
        shipping_price=shipping_price,
        order_items=line_items,
        custom_attributes=[
            CustomAttribute(attribute_key="shopify_order_id", attribute_value=order.id)
        ],
    )
