"""add subtitle tracks to media assets

Revision ID: 0007_subtitle_tracks
Revises: 0006_media_asset_metadata
Create Date: 2026-09-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0007_subtitle_tracks"
down_revision = "0006_media_asset_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column(
            "subtitle_tracks_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_table(
        "subtitle_tracks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("media_asset_id", sa.UUID(), nullable=False),
        sa.Column("stream_index", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("codec_name", sa.String(length=64), nullable=True),
        sa.Column("source_path", sa.String(length=2000), nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_forced",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id"],
            ["media_assets.id"],
            name="fk_subtitle_tracks_media_asset_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "media_asset_id",
            "stream_index",
            name="uq_subtitle_tracks_asset_stream",
        ),
    )


def downgrade() -> None:
    op.drop_table("subtitle_tracks")
    op.drop_column("media_assets", "subtitle_tracks_updated_at")
