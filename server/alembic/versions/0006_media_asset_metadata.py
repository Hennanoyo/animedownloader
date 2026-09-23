"""add current media metadata to media assets

Revision ID: 0006_media_asset_metadata
Revises: 0005_media_asset
Create Date: 2026-09-23
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_media_asset_metadata"
down_revision = "0005_media_asset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column("format_name", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("video_codec", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("audio_codec", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("width", sa.Integer(), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("height", sa.Integer(), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("frame_rate", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column(
            "metadata_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("media_assets", "metadata_updated_at")
    op.drop_column("media_assets", "frame_rate")
    op.drop_column("media_assets", "height")
    op.drop_column("media_assets", "width")
    op.drop_column("media_assets", "audio_codec")
    op.drop_column("media_assets", "video_codec")
    op.drop_column("media_assets", "size_bytes")
    op.drop_column("media_assets", "duration_seconds")
    op.drop_column("media_assets", "format_name")
