"""production delivery queue

Revision ID: 0002_delivery_queue_production
Revises: 0001_initial_schema
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_delivery_queue_production"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("delivery_jobs", sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("delivery_jobs", sa.Column("last_error_code", sa.String(length=64), nullable=True))
    op.add_column("delivery_jobs", sa.Column("lock_token", sa.String(length=64), nullable=True))
    op.add_column("delivery_jobs", sa.Column("lock_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("delivery_jobs", sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE delivery_jobs SET available_at = next_attempt_at WHERE available_at IS NULL")

    op.create_index("ix_delivery_jobs_available_at", "delivery_jobs", ["available_at"])
    op.create_index("ix_delivery_jobs_lock_token", "delivery_jobs", ["lock_token"])
    op.create_index("ix_delivery_jobs_lock_expires_at", "delivery_jobs", ["lock_expires_at"])


def downgrade() -> None:
    op.drop_index("ix_delivery_jobs_lock_expires_at", table_name="delivery_jobs")
    op.drop_index("ix_delivery_jobs_lock_token", table_name="delivery_jobs")
    op.drop_index("ix_delivery_jobs_available_at", table_name="delivery_jobs")
    op.drop_column("delivery_jobs", "dead_lettered_at")
    op.drop_column("delivery_jobs", "lock_expires_at")
    op.drop_column("delivery_jobs", "lock_token")
    op.drop_column("delivery_jobs", "last_error_code")
    op.drop_column("delivery_jobs", "available_at")
