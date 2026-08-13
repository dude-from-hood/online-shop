"""Add transactional outbox events."""

from typing import Sequence, Union

from alembic import op


revision: str = "0002_add_outbox_events"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE outbox_events (
            id UUID PRIMARY KEY,
            event_type VARCHAR(100) NOT NULL,
            aggregate_type VARCHAR(100) NOT NULL,
            aggregate_id BIGINT NOT NULL,
            payload JSONB NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING', 'PROCESSED', 'FAILED')),
            attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            processed_at TIMESTAMPTZ,
            error_message TEXT
        )
    """)
    op.execute("""
        CREATE INDEX ix_outbox_events_pending
        ON outbox_events (status, available_at)
        WHERE status IN ('PENDING', 'FAILED')
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS outbox_events")
