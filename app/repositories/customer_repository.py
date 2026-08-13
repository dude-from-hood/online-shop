from datetime import datetime

import psycopg


CustomerRow = tuple[int, str, str, datetime]


class CustomerRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def create(self, name: str, email: str) -> CustomerRow:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO customers (name, email)
                VALUES (%s, %s)
                RETURNING id, name, email, created_at
                """,
                (name, email),
            )
            row = cursor.fetchone()

        assert row is not None
        return row

    def get_by_id(self, customer_id: int) -> CustomerRow | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, email, created_at
                FROM customers
                WHERE id = %s
                """,
                (customer_id,),
            )
            return cursor.fetchone()

    def delete(self, customer_id: int) -> bool:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM customers WHERE id = %s",
                (customer_id,),
            )
            return cursor.rowcount == 1
