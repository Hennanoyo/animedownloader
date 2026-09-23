"""add thumbnail sprite state to media assets

Revision ID: 0011_media_thumbnails
Revises: 0010_chapter_id_bigint
Create Date: 2026-09-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0011_media_thumbnails"
down_revision = "0010_chapter_id_bigint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column(
            "thumbnail_status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "media_assets",
        sa.Column("thumbnail_sprite_path", sa.String(length=2000), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("thumbnail_vtt_path", sa.String(length=2000), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column(
            "thumbnail_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "media_assets",
        sa.Column("thumbnail_error_message", sa.String(length=2000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("media_assets", "thumbnail_error_message")
    op.drop_column("media_assets", "thumbnail_updated_at")
    op.drop_column("media_assets", "thumbnail_vtt_path")
    op.drop_column("media_assets", "thumbnail_sprite_path")
    op.drop_column("media_assets", "thumbnail_status")
