"""rename media transcoding jobs to media preparation jobs

Revision ID: 0013_media_preparation
Revises: 0012_media_playable
Create Date: 2026-09-24
"""

from alembic import op

revision = "0013_media_preparation"
down_revision = "0012_media_playable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("media_transcoding_jobs", "media_preparation_jobs")
    op.execute(
        "ALTER INDEX ix_media_transcoding_jobs_media_asset_id "
        "RENAME TO ix_media_preparation_jobs_media_asset_id",
    )
    op.execute(
        "ALTER INDEX ix_media_transcoding_jobs_variant_id "
        "RENAME TO ix_media_preparation_jobs_variant_id",
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX ix_media_preparation_jobs_variant_id "
        "RENAME TO ix_media_transcoding_jobs_variant_id",
    )
    op.execute(
        "ALTER INDEX ix_media_preparation_jobs_media_asset_id "
        "RENAME TO ix_media_transcoding_jobs_media_asset_id",
    )
    op.rename_table("media_preparation_jobs", "media_transcoding_jobs")
