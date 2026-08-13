import psycopg

from app.api.schemas.orders import OrderItemCreate, OrderStatus


OrderRow = tuple[int, int, str, int | None, str | None, int | None, object | None]


class OrderRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def create_customer(self, name: str, email: str) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO customers (name, email)
                VALUES (%s, %s)
                ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                (name, email),
            )
            row = cursor.fetchone()
        assert row is not None
        return row[0]

    def create_order(self, customer_id: int, idempotency_key: str | None = None, request_hash: str | None = None) -> tuple[int, str, bool]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO orders (customer_id, idempotency_key, request_hash)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id, status
                """,
                (customer_id, idempotency_key, request_hash),
            )
            row = cursor.fetchone()
        if row is not None:
            return row[0], row[1], True

        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, status FROM orders WHERE idempotency_key = %s",
                (idempotency_key,),
            )
            existing_row = cursor.fetchone()
        assert existing_row is not None
        return existing_row[0], existing_row[1], False

    def get_orders_by_idempotency_key(self, idempotency_key: str) -> tuple[int, str] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, status FROM orders WHERE idempotency_key = %s",
                (idempotency_key,),
            )
            return cursor.fetchone()

    def get_order_request_hash(self, order_id: int) -> str | None:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT request_hash FROM orders WHERE id = %s", (order_id,))
            row = cursor.fetchone()
        assert row is not None
        return row[0]

    def create_order_item(self, order_id: int, item: OrderItemCreate) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO order_items (order_id, product_name, quantity, price)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (order_id, item.product_name, item.quantity, item.price),
            )
            row = cursor.fetchone()
        assert row is not None
        return row[0]

    def get_orders(
            self,
            order_id: int | None = None,
            date_from=None,
            date_to=None,
            order_ids: list[int] | None = None,
    ) -> list[OrderRow]:
        query = """
            SELECT
                o.id, o.customer_id, o.status,
                oi.id, oi.product_name, oi.quantity, oi.price
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
        """
        conditions: list[str] = []
        parameters: list[object] = []

        if order_id is not None:
            conditions.append("o.id = %s")
            parameters.append(order_id)

        if date_from is not None and date_to is not None:
            conditions.append("o.created_at >= %s AND o.created_at <= %s")
            parameters.extend([date_from, date_to])

        if order_ids is not None:
            conditions.append("o.id = ANY(%s)")
            parameters.append(order_ids)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY o.id DESC, oi.id"

        with self.connection.cursor() as cursor:
            cursor.execute(query, tuple(parameters))
            return cursor.fetchall()

    def update_order_status(self, order_id: int, new_status: OrderStatus) -> str:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE orders
                SET status = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING status
                """,
                (new_status.value, order_id),
            )
            row = cursor.fetchone()
        assert row is not None
        return row[0]
