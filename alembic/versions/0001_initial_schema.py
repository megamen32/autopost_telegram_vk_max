"""initial schema"""

from alembic import op
import sqlalchemy as sa

revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sync_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('source_platform', sa.String(length=32), nullable=False),
        sa.Column('target_platform', sa.String(length=32), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('allow_text', sa.Boolean(), nullable=False),
        sa.Column('allow_images', sa.Boolean(), nullable=False),
        sa.Column('allow_video', sa.Boolean(), nullable=False),
        sa.Column('allow_audio', sa.Boolean(), nullable=False),
        sa.Column('allow_documents', sa.Boolean(), nullable=False),
        sa.Column('allow_reposts', sa.Boolean(), nullable=False),
        sa.Column('max_images', sa.Integer(), nullable=True),
        sa.Column('max_video_size_mb', sa.Integer(), nullable=True),
        sa.Column('max_audio_size_mb', sa.Integer(), nullable=True),
        sa.Column('drop_unsupported_media', sa.Boolean(), nullable=False),
        sa.Column('repost_mode', sa.String(length=32), nullable=False),
        sa.Column('copy_text_template', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.UniqueConstraint('source_platform', 'target_platform', name='uq_sync_rules_pair'),
    )

    op.create_table(
        'routes',
        sa.Column('id', sa.String(length=128), primary_key=True),
        sa.Column('source_platform', sa.String(length=32), nullable=False),
        sa.Column('source_chat_id', sa.String(length=255), nullable=False),
        sa.Column('target_platform', sa.String(length=32), nullable=False),
        sa.Column('target_chat_id', sa.String(length=255), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_routes_source_platform', 'routes', ['source_platform'])
    op.create_index('ix_routes_source_chat_id', 'routes', ['source_chat_id'])

    op.create_table(
        'processed_events',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('source_platform', sa.String(length=32), nullable=False),
        sa.Column('source_chat_id', sa.String(length=255), nullable=False),
        sa.Column('source_message_id', sa.String(length=255), nullable=False),
        sa.Column('content_hash', sa.String(length=128), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.UniqueConstraint('source_platform', 'source_chat_id', 'source_message_id', name='uq_processed_events_source_message'),
    )

    op.create_table(
        'message_links',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('origin_platform', sa.String(length=32), nullable=False),
        sa.Column('origin_chat_id', sa.String(length=255), nullable=False),
        sa.Column('origin_message_id', sa.String(length=255), nullable=False),
        sa.Column('target_platform', sa.String(length=32), nullable=False),
        sa.Column('target_chat_id', sa.String(length=255), nullable=False),
        sa.Column('target_message_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('message_links')
    op.drop_table('processed_events')
    op.drop_index('ix_routes_source_chat_id', table_name='routes')
    op.drop_index('ix_routes_source_platform', table_name='routes')
    op.drop_table('routes')
    op.drop_table('sync_rules')
