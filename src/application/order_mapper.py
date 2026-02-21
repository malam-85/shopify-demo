from uuid import UUID

from src.domain.everstox_order import (
    BillingAddress,
    CustomAttribute,
    EverstoxOrder,
    OrderItem,
    Product,
    ShippingAddress,
    ShippingPrice,
)
from src.domain.order import Order, OrderBillingAddress, OrderShippingAddress

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

    return EverstoxOrder(
        shop_instance_id=_SHOP_INSTANCE_ID,
        order_number=order.name,
        order_date=order.created_at,
        customer_email="todo@example.com",  # TODO: from Shopify customer field
        financial_status=order.financial_status,
        shipping_address=shipping_address,
        billing_address=billing_address,
        shipping_price=ShippingPrice(  # TODO: from Shopify shippingLine field
            currency=order.currency,
            price_net_after_discount=0.0,
            tax_amount=0.0,
            tax_rate=0.0,
            price=0.0,
            tax=0.0,
            discount=0.0,
            discount_gross=0.0,
        ),
        order_items=[
            OrderItem(
                quantity=1, product=Product(sku="TODO")
            )  # TODO: from Shopify lineItems
        ],
        custom_attributes=[
            CustomAttribute(attribute_key="shopify_order_id", attribute_value=order.id)
        ],
    )
