"""platform settings encrypted secrets

Revision ID: 0003_platform_settings_encrypted
Revises: 0002_delivery_queue_production
Create Date: 2026-04-01 15:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_platform_settings_encrypted"
down_revision = "0002_delivery_queue_production"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("platform", sa.String(length=32), primary_key=True),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("secrets_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("platform_settings")
