import psycopg
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.api.schemas.orders import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.order_service import (
    InvalidOrderDateIntervalError,
    InvalidOrderIdsError,
    InvalidOrderStatusTransitionError,
    IdempotencyKeyConflictError,
    OrderNotFoundError,
    OrderService,
)


router = APIRouter(prefix="/orders", tags=["Orders"])
service = OrderService()


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
        payload: OrderCreate,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> OrderResponse:
    try:
        return service.create_order(payload, idempotency_key)
    except IdempotencyKeyConflictError as error:
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key was already used with a different payload",
        ) from error
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Could not create order") from error


@router.get("", response_model=list[OrderResponse])
def get_orders() -> list[OrderResponse]:
    try:
        return service.get_orders()
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Could not fetch orders") from error


@router.get("/search", response_model=list[OrderResponse])
def search_orders(
        date_from: datetime = Query(...),
        date_to: datetime = Query(...),
        order_ids: list[int] | None = Query(default=None),
) -> list[OrderResponse]:
    try:
        return service.search_orders(date_from, date_to, order_ids)
    except InvalidOrderIdsError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except InvalidOrderDateIntervalError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Could not search orders") from error


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int) -> OrderResponse:
    try:
        return service.get_order(order_id)
    except OrderNotFoundError as error:
        raise HTTPException(status_code=404, detail="Order not found") from error
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Could not fetch order") from error


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(order_id: int, payload: OrderStatusUpdate) -> OrderResponse:
    try:
        return service.update_order_status(order_id, payload.status)
    except OrderNotFoundError as error:
        raise HTTPException(status_code=404, detail="Order not found") from error
    except InvalidOrderStatusTransitionError as error:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change status from {error.current_status} to {error.requested_status}",
        ) from error
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Could not update order status") from error
