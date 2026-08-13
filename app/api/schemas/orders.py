from enum import StrEnum

from pydantic import BaseModel, Field

"""
gt=0    строго больше 0
ge=0    больше или равно 0
lt=100  строго меньше 100
le=99   меньше или равно 99
"""

class OrderStatus(StrEnum):
    NEW = "NEW"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class OrderItemCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=30)
    quantity: int = Field(gt=0, le=99)
    price: int = Field(ge=0)


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=30)
    customer_email: str = Field(min_length=3, max_length=50, pattern=r"^[^@\s]+@[^@\s]+$")
    items: list[OrderItemCreate] = Field(min_length=1, max_length=10)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemResponse(BaseModel):
    id: int
    product_name: str
    quantity: int
    price: int = Field(ge=0, examples=[19])

class OrderResponse(BaseModel):
    id: int
    customer_id: int
    status: OrderStatus
    items: list[OrderItemResponse]
