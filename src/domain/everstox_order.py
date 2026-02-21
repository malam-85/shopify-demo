"""DTO for the Everstox create-order API payload."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class AddressType(StrEnum):
    private = "private"
    business = "business"


class ShippingAddress(BaseModel):
    first_name: str
    last_name: str
    country_code: str
    city: str
    zip: str
    address_1: str
    address_2: str | None = None
    company: str | None = None
    phone: str | None = None
    title: str | None = None
    country: str | None = None
    province_code: str | None = None
    province: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    contact_person: str | None = None
    department: str | None = None
    sub_department: str | None = None
    address_type: AddressType | None = None


class BillingAddress(BaseModel):
    first_name: str
    last_name: str
    country_code: str
    city: str
    zip: str
    address_1: str
    address_2: str | None = None
    company: str | None = None
    phone: str | None = None
    title: str | None = None
    country: str | None = None
    province_code: str | None = None
    province: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    VAT_number: str | None = None  # noqa: N815  (matches API field name exactly)
    contact_person: str | None = None
    department: str | None = None
    sub_department: str | None = None
    address_type: AddressType | None = None


class ShippingPrice(BaseModel):
    currency: str
    price_net_after_discount: float
    tax_amount: float
    tax_rate: float
    price: float
    tax: float
    discount: float
    discount_gross: float


class CustomAttribute(BaseModel):
    attribute_key: str
    attribute_value: str


class ShipmentOption(BaseModel):
    id: UUID | None = None
    name: str | None = None


class PriceSet(BaseModel):
    quantity: int
    currency: str
    price_net_after_discount: float
    tax_amount: float
    tax_rate: float
    price: float
    tax: float
    discount: float
    discount_gross: float


class Product(BaseModel):
    sku: str


class OrderItem(BaseModel):
    quantity: int = Field(..., ge=1)
    product: Product
    shipment_options: list[ShipmentOption] = Field(default_factory=list)
    price_set: list[PriceSet] = Field(default_factory=list)
    custom_attributes: list[CustomAttribute] = Field(default_factory=list)
    requested_batch: str | None = None
    requested_batch_expiration_date: datetime | None = None
    picking_hint: str | None = None
    packing_hint: str | None = None


class Attachment(BaseModel):
    attachment_type: str
    url: str | None = None
    content: str | None = None
    file_name: str | None = None


class EverstoxOrder(BaseModel):
    """Top-level DTO sent to the Everstox create-order endpoint."""

    shop_instance_id: UUID
    order_number: str
    order_date: datetime
    customer_email: str
    financial_status: str
    shipping_address: ShippingAddress
    billing_address: BillingAddress
    shipping_price: ShippingPrice
    order_items: list[OrderItem]
    payment_method_id: UUID | None = None
    payment_method_name: str | None = None
    requested_warehouse_id: UUID | None = None
    requested_warehouse_name: str | None = None
    requested_delivery_date: datetime | None = None
    order_priority: int | None = Field(default=None, ge=1, le=99)
    picking_date: datetime | None = None
    print_return_label: bool = False
    picking_hint: str | None = None
    packing_hint: str | None = None
    order_type: str | None = None
    custom_attributes: list[CustomAttribute] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
