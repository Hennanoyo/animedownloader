"""add CMAF streaming packages and packaging jobs

Revision ID: 0014_media_packaging
Revises: 0013_media_preparation
Create Date: 2026-09-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0014_media_packaging"
down_revision = "0013_media_preparation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_streaming_packages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("media_variant_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("source_path", sa.String(length=2000), nullable=False),
        sa.Column(
            "source_variant_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("hls_master_key", sa.String(length=2000), nullable=True),
        sa.Column("dash_manifest_key", sa.String(length=2000), nullable=True),
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
            ["media_variant_id"],
            ["media_variants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "media_variant_id",
            name="uq_media_streaming_packages_media_variant",
        ),
    )
    op.create_index(
        "ix_media_streaming_packages_media_variant_id",
        "media_streaming_packages",
        ["media_variant_id"],
    )

    op.create_table(
        "media_streaming_representations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("package_id", sa.UUID(), nullable=False),
        sa.Column("quality", sa.String(length=32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("bandwidth", sa.BigInteger(), nullable=False),
        sa.Column("video_codec", sa.String(length=64), nullable=False),
        sa.Column("audio_codec", sa.String(length=64), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("hls_playlist_key", sa.String(length=2000), nullable=False),
        sa.Column("init_segment_key", sa.String(length=2000), nullable=False),
        sa.Column("segment_directory_key", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
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
            ["package_id"],
            ["media_streaming_packages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "package_id",
            "quality",
            name="uq_media_streaming_representations_package_quality",
        ),
    )
    op.create_index(
        "ix_media_streaming_representations_package_id",
        "media_streaming_representations",
        ["package_id"],
    )

    op.create_table(
        "media_packaging_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("media_variant_id", sa.UUID(), nullable=False),
        sa.Column("package_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("source_path", sa.String(length=2000), nullable=False),
        sa.Column(
            "source_variant_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
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
            ["media_variant_id"],
            ["media_variants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["media_streaming_packages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_media_packaging_jobs_media_variant_id",
        "media_packaging_jobs",
        ["media_variant_id"],
    )
    op.create_index(
        "ix_media_packaging_jobs_package_id",
        "media_packaging_jobs",
        ["package_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_media_packaging_jobs_package_id",
        table_name="media_packaging_jobs",
    )
    op.drop_index(
        "ix_media_packaging_jobs_media_variant_id",
        table_name="media_packaging_jobs",
    )
    op.drop_table("media_packaging_jobs")
    op.drop_index(
        "ix_media_streaming_representations_package_id",
        table_name="media_streaming_representations",
    )
    op.drop_table("media_streaming_representations")
    op.drop_index(
        "ix_media_streaming_packages_media_variant_id",
        table_name="media_streaming_packages",
    )
    op.drop_table("media_streaming_packages")
