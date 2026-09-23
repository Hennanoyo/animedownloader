"""add subtitle processing state

Revision ID: 0008_subtitle_processing
Revises: 0007_subtitle_tracks
Create Date: 2026-09-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0008_subtitle_processing"
down_revision = "0007_subtitle_tracks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column(
            "subtitle_tracks_processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "subtitle_tracks",
        sa.Column("normalized_path", sa.String(length=2000), nullable=True),
    )
    op.add_column(
        "subtitle_tracks",
        sa.Column("normalized_format", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "subtitle_tracks",
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "subtitle_tracks",
        sa.Column("error_message", sa.String(length=2000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subtitle_tracks", "error_message")
    op.drop_column("subtitle_tracks", "status")
    op.drop_column("subtitle_tracks", "normalized_format")
    op.drop_column("subtitle_tracks", "normalized_path")
    op.drop_column("media_assets", "subtitle_tracks_processed_at")
