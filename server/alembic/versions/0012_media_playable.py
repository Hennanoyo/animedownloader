"""add playable media variants and transcoding jobs

Revision ID: 0012_media_playable
Revises: 0011_media_thumbnails
Create Date: 2026-09-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0012_media_playable"
down_revision = "0011_media_thumbnails"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_variants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("media_asset_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("source_path", sa.String(length=2000), nullable=True),
        sa.Column("source_metadata_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("path", sa.String(length=2000), nullable=True),
        sa.Column("format_name", sa.String(length=128), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("video_codec", sa.String(length=64), nullable=True),
        sa.Column("audio_codec", sa.String(length=64), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("frame_rate", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
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
            name="fk_media_variants_media_asset_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "media_asset_id",
            "kind",
            name="uq_media_variants_asset_kind",
        ),
    )
    op.create_index(
        "ix_media_variants_media_asset_id",
        "media_variants",
        ["media_asset_id"],
    )

    op.create_table(
        "media_transcoding_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("media_asset_id", sa.UUID(), nullable=False),
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=True),
        sa.Column("source_path", sa.String(length=2000), nullable=False),
        sa.Column(
            "source_metadata_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("output_path", sa.String(length=2000), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_media_transcoding_jobs_media_asset_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["media_variants.id"],
            name="fk_media_transcoding_jobs_variant_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_media_transcoding_jobs_media_asset_id",
        "media_transcoding_jobs",
        ["media_asset_id"],
    )
    op.create_index(
        "ix_media_transcoding_jobs_variant_id",
        "media_transcoding_jobs",
        ["variant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_media_transcoding_jobs_variant_id",
        table_name="media_transcoding_jobs",
    )
    op.drop_index(
        "ix_media_transcoding_jobs_media_asset_id",
        table_name="media_transcoding_jobs",
    )
    op.drop_table("media_transcoding_jobs")
    op.drop_index(
        "ix_media_variants_media_asset_id",
        table_name="media_variants",
    )
    op.drop_table("media_variants")
