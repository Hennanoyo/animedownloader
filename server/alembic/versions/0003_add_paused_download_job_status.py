"""add paused download job status

Revision ID: 0003_add_paused_download_job_status
Revises: 0002_create_download_jobs
Create Date: 2026-09-23
"""

from alembic import op

revision = "0003_add_paused_download_job_status"
down_revision = "0002_create_download_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("uq_download_jobs_episode_active", table_name="download_jobs")
    op.create_index(
        "uq_download_jobs_episode_active",
        "download_jobs",
        ["episode_id"],
        unique=True,
        postgresql_where=op.inline_literal(
            "status IN ('pending', 'downloading', 'paused')",
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_download_jobs_episode_active", table_name="download_jobs")
    op.create_index(
        "uq_download_jobs_episode_active",
        "download_jobs",
        ["episode_id"],
        unique=True,
        postgresql_where=op.inline_literal(
            "status IN ('pending', 'downloading')",
        ),
    )
