"""create media assets

Revision ID: 0005_media_asset
Revises: 0004_media_processing
Create Date: 2026-09-23
"""

import sqlalchemy as sa

from alembic import op

revision = "0005_media_asset"
down_revision = "0004_media_processing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("processing_job_id", sa.UUID(), nullable=True),
        sa.Column("path", sa.String(length=2000), nullable=False),
        sa.Column("format_name", sa.String(length=128), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("video_codec", sa.String(length=64), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("frame_rate", sa.String(length=32), nullable=True),
        sa.Column("audio_codec", sa.String(length=64), nullable=True),
        sa.Column("audio_channels", sa.Integer(), nullable=True),
        sa.Column("audio_sample_rate_hz", sa.Integer(), nullable=True),
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
            ["episode_id"],
            ["episodes.id"],
            name="fk_media_assets_episode_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["processing_job_id"],
            ["media_processing_jobs.id"],
            name="fk_media_assets_processing_job_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "episode_id",
            name="uq_media_assets_episode",
        ),
        sa.UniqueConstraint(
            "processing_job_id",
            name="uq_media_assets_processing_job",
        ),
    )


def downgrade() -> None:
    op.drop_table("media_assets")
