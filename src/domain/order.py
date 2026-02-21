from datetime import datetime

from pydantic import BaseModel


class OrderShippingAddress(BaseModel):
    """Shipping address as returned by the Shopify Admin GraphQL API."""

    first_name: str
    last_name: str
    country_code: str
    city: str
    zip: str
    address_1: str
    address_2: str | None = None
    phone: str | None = None
    province: str | None = None


class OrderBillingAddress(BaseModel):
    """Billing address as returned by the Shopify Admin GraphQL API."""

    first_name: str
    last_name: str
    country_code: str
    city: str
    zip: str
    address_1: str
    address_2: str | None = None
    company: str | None = None
    phone: str | None = None
    country: str | None = None
    province: str | None = None
    province_code: str | None = None


class Order(BaseModel):
    """Domain model representing a Shopify order."""

    id: str  # Shopify GID, e.g. "gid://shopify/Order/123"
    name: str  # Human-readable order number, e.g. "#1001"
    created_at: datetime
    financial_status: str  # e.g. "PAID"
    fulfillment_status: str | None  # e.g. "UNFULFILLED", "PARTIAL", None
    total_price: str
    currency: str
    shipping_address: OrderShippingAddress | None = None
    billing_address: OrderBillingAddress | None = None
