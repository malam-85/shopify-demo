from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


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


class OrderTaxLine(BaseModel):
    rate: float  # e.g. 0.19 for 19%
    amount: float  # absolute tax amount in currency
    currency: str


class OrderShippingLine(BaseModel):
    title: str | None = None  # e.g. "Standard Shipping"
    code: str | None = None  # carrier code
    original_price: float
    discounted_price: float
    currency: str
    tax_lines: list[OrderTaxLine] = Field(default_factory=list)


class OrderLineItem(BaseModel):
    id: str
    title: str
    quantity: int
    sku: str
    price: float
    currency: str
    tax_lines: list[OrderTaxLine] = Field(default_factory=list)
    discount_total: float = 0.0
    custom_attributes: list[dict] = Field(default_factory=list)


class Order(BaseModel):
    """Domain model representing a Shopify order."""

    id: str  # Shopify GID, e.g. "gid://shopify/Order/123"
    name: str  # Human-readable order number, e.g. "#1001"
    created_at: datetime
    financial_status: str  # e.g. "PAID"
    fulfillment_status: str | None  # e.g. "UNFULFILLED", "PARTIAL", None
    total_price: str
    currency: str
    tags: list[str] = Field(default_factory=list)
    email: str | None = None
    shipping_address: OrderShippingAddress | None = None
    billing_address: OrderBillingAddress | None = None
    shipping_line: OrderShippingLine | None = None
    line_items: List[OrderLineItem] = Field(default_factory=list)
