"""create download jobs

Revision ID: 0002_create_download_jobs
Revises: 0001_create_anime_and_episode
Create Date: 2026-09-23
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_create_download_jobs"
down_revision = "0001_create_anime_and_episode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "download_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("episode_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "downloaded_bytes",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("total_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "downloaded_bytes >= 0",
            name="ck_download_jobs_downloaded_bytes_nonnegative",
        ),
        sa.CheckConstraint(
            "total_bytes IS NULL OR total_bytes >= 0",
            name="ck_download_jobs_total_bytes_nonnegative",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_download_jobs_attempt_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["episodes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_download_jobs_episode_id"),
        "download_jobs",
        ["episode_id"],
        unique=False,
    )
    op.create_index(
        "uq_download_jobs_episode_active",
        "download_jobs",
        ["episode_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'downloading')"),
    )


def downgrade() -> None:
    op.drop_index("uq_download_jobs_episode_active", table_name="download_jobs")
    op.drop_index(op.f("ix_download_jobs_episode_id"), table_name="download_jobs")
    op.drop_table("download_jobs")
