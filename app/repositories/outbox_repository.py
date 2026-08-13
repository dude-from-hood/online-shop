import json
from uuid import UUID, uuid4

import psycopg


class OutboxRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def create_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: int,
        payload: dict,
    ) -> UUID:
        event_id = uuid4()
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO outbox_events (
                    id, event_type, aggregate_type, aggregate_id, payload
                )
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    event_id,
                    event_type,
                    aggregate_type,
                    aggregate_id,
                    json.dumps(payload),
                ),
            )
        return event_id

    def get_pending_events(self, limit: int = 100) -> list[dict]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, event_type, aggregate_type, aggregate_id, payload
                FROM outbox_events
                WHERE status = 'PENDING' AND available_at <= NOW()
                ORDER BY created_at
                LIMIT %s
                """,
                (limit,),
            )
            columns = [description.name for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def mark_as_processed(self, event_id: UUID) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE outbox_events
                SET status = 'PROCESSED', processed_at = NOW()
                WHERE id = %s AND status = 'PENDING'
                """,
                (event_id,),
            )

    def mark_as_failed(self, event_id: UUID, error_message: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE outbox_events
                SET status = 'FAILED', attempts = attempts + 1,
                    error_message = %s, available_at = NOW() + INTERVAL '10 seconds'
                WHERE id = %s AND status = 'PENDING'
                """,
                (error_message[:1000], event_id),
            )
