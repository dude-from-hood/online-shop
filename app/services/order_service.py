import hashlib
import psycopg
from datetime import datetime, timedelta, timezone

from app.api.schemas.orders import (
    OrderCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatus,
)
from app.core.config import settings
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.order_repository import OrderRepository, OrderRow


class OrderNotFoundError(Exception):
    pass


class InvalidOrderDateIntervalError(Exception):
    pass


class InvalidOrderIdsError(Exception):
    pass


class IdempotencyKeyConflictError(Exception):
    pass


class InvalidOrderStatusTransitionError(Exception):
    def __init__(self, current_status: OrderStatus, requested_status: OrderStatus) -> None:
        self.current_status = current_status
        self.requested_status = requested_status


class OrderService:

    # бизнес-правила переходов статуса заказа
    allowed_transitions: dict[OrderStatus, set[OrderStatus]] = {
        OrderStatus.NEW: {OrderStatus.PAID, OrderStatus.CANCELLED},
        OrderStatus.PAID: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
        OrderStatus.CANCELLED: set(),
        OrderStatus.COMPLETED: set(),
    }

    def create_order(self, data: OrderCreate, idempotency_key: str | None = None) -> OrderResponse:
        with psycopg.connect(settings.database_url) as connection:
            repository = OrderRepository(connection)
            request_hash = hashlib.sha256(
                data.model_dump_json().encode("utf-8")
            ).hexdigest()

            if idempotency_key is not None:
                existing_order = repository.get_orders_by_idempotency_key(idempotency_key)
                if existing_order is not None:
                    if repository.get_order_request_hash(existing_order[0]) != request_hash:
                        raise IdempotencyKeyConflictError
                    return self._build_responses(repository.get_orders(existing_order[0]))[0]

            customer_id = repository.create_customer(data.customer_name, data.customer_email)
            order_id, status, created = repository.create_order(
                customer_id, idempotency_key, request_hash
            )
            if not created:
                if repository.get_order_request_hash(order_id) != request_hash:
                    raise IdempotencyKeyConflictError
                return self._build_responses(repository.get_orders(order_id))[0]

            response_items: list[OrderItemResponse] = []
            for item in data.items:
                item_id = repository.create_order_item(order_id, item)
                response_items.append(
                    OrderItemResponse(
                        id=item_id,
                        product_name=item.product_name,
                        quantity=item.quantity,
                        price=item.price,
                    )
                )

            OutboxRepository(connection).create_event(
                event_type="OrderCreated",
                aggregate_type="order",
                aggregate_id=order_id,
                payload={
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "status": OrderStatus(status).value,
                },
            )

            return OrderResponse(
                id=order_id,
                customer_id=customer_id,
                status=OrderStatus(status),
                items=response_items,
            )

    def get_orders(self) -> list[OrderResponse]:
        with psycopg.connect(settings.database_url) as connection:
            rows = OrderRepository(connection).get_orders()
        return self._build_responses(rows)

    def search_orders(
            self,
            date_from: datetime,
            date_to: datetime,
            order_ids: list[int] | None = None,
    ) -> list[OrderResponse]:
        if order_ids is not None and any(order_id <= 0 for order_id in order_ids):
            raise InvalidOrderIdsError("order_ids must contain only positive integers")

        utc_now = datetime.now(timezone.utc)
        if date_from.tzinfo is None:
            date_from = date_from.replace(tzinfo=timezone.utc)
        if date_to.tzinfo is None:
            date_to = date_to.replace(tzinfo=timezone.utc)

        if date_from > date_to:
            raise InvalidOrderDateIntervalError(
                "date_from must be earlier than or equal to date_to"
            )
        if date_to > utc_now:
            raise InvalidOrderDateIntervalError(
                "date_to cannot be in the future"
            )
        if date_to - date_from > timedelta(days=30):
            raise InvalidOrderDateIntervalError(
                "date range cannot exceed 30 days"
            )

        with psycopg.connect(settings.database_url) as connection:
            rows = OrderRepository(connection).get_orders(
                date_from=date_from,
                date_to=date_to,
                order_ids=order_ids,
            )

        return self._build_responses(rows)

    def get_order(self, order_id: int) -> OrderResponse:
        with psycopg.connect(settings.database_url) as connection:
            rows = OrderRepository(connection).get_orders(order_id)

        if not rows:
            raise OrderNotFoundError

        return self._build_responses(rows)[0]

    def update_order_status(self, order_id: int, new_status: OrderStatus) -> OrderResponse:
        with psycopg.connect(settings.database_url) as connection:
            repository = OrderRepository(connection)
            rows = repository.get_orders(order_id)

            if not rows:
                raise OrderNotFoundError

            current_status = OrderStatus(rows[0][2])
            allowed_statuses = self.allowed_transitions[current_status]
            if new_status not in allowed_statuses:
                raise InvalidOrderStatusTransitionError(current_status, new_status)

            repository.update_order_status(order_id, new_status)
            OutboxRepository(connection).create_event(
                event_type="OrderStatusChanged",
                aggregate_type="order",
                aggregate_id=order_id,
                payload={
                    "order_id": order_id,
                    "old_status": current_status.value,
                    "new_status": new_status.value,
                },
            )
            updated_rows = repository.get_orders(order_id)

        return self._build_responses(updated_rows)[0]

    @staticmethod
    def _build_responses(rows: list[OrderRow]) -> list[OrderResponse]:
        responses: dict[int, OrderResponse] = {}

        for row in rows:
            order_id, customer_id, status, item_id, product_name, quantity, price = row
            if order_id not in responses:
                responses[order_id] = OrderResponse(
                    id=order_id,
                    customer_id=customer_id,
                    status=OrderStatus(status),
                    items=[],
                )

            if item_id is not None:
                responses[order_id].items.append(
                    OrderItemResponse(
                        id=item_id,
                        product_name=product_name or "",
                        quantity=quantity or 0,
                        price=price or 0,
                    )
                )

        return list(responses.values())
