"""Add idempotency fields to orders."""

from typing import Sequence, Union

from alembic import op


revision: str = "0003_add_order_idempotency"
down_revision: Union[str, None] = "0002_add_outbox_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE orders ADD COLUMN idempotency_key VARCHAR(255)")
    op.execute("ALTER TABLE orders ADD COLUMN request_hash VARCHAR(64)")
    op.execute("CREATE UNIQUE INDEX ux_orders_idempotency_key ON orders(idempotency_key) WHERE idempotency_key IS NOT NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_orders_idempotency_key")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS request_hash")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS idempotency_key")
