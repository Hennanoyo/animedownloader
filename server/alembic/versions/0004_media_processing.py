"""create media processing jobs

Revision ID: 0004_media_processing
Revises: 0003_paused_download_status
Create Date: 2026-09-23
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_media_processing"
down_revision = "0003_paused_download_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_processing_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("download_job_id", sa.UUID(), nullable=True),
        sa.Column("download_directory", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("media_path", sa.String(length=2000), nullable=True),
        sa.Column("probe_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
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
            ["download_job_id"],
            ["download_jobs.id"],
            name="fk_media_processing_jobs_download_job_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["episodes.id"],
            name="fk_media_processing_jobs_episode_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "download_job_id",
            name="uq_media_processing_jobs_download_job",
        ),
    )
    op.create_index(
        "ix_media_processing_jobs_episode_id",
        "media_processing_jobs",
        ["episode_id"],
        unique=False,
    )
    op.create_index(
        "uq_media_processing_jobs_episode_active",
        "media_processing_jobs",
        ["episode_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('pending', 'processing')",
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_media_processing_jobs_episode_active",
        table_name="media_processing_jobs",
    )
    op.drop_index(
        "ix_media_processing_jobs_episode_id",
        table_name="media_processing_jobs",
    )
    op.drop_table("media_processing_jobs")
