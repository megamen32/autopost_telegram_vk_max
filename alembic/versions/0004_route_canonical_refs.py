"""add canonical refs to routes

Revision ID: 0004_route_canonical_refs
Revises: 0003_platform_settings_encrypted
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_route_canonical_refs"
down_revision = "0003_platform_settings_encrypted"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("routes", sa.Column("source_chat_canonical", sa.String(length=255), nullable=True))
    op.add_column("routes", sa.Column("target_chat_canonical", sa.String(length=255), nullable=True))
    op.create_index("ix_routes_source_chat_canonical", "routes", ["source_chat_canonical"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_routes_source_chat_canonical", table_name="routes")
    op.drop_column("routes", "target_chat_canonical")
    op.drop_column("routes", "source_chat_canonical")
