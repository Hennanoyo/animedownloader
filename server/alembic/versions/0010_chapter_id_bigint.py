"""store media chapter ids as bigint

Revision ID: 0010_chapter_id_bigint
Revises: 0009_media_resources
Create Date: 2026-09-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0010_chapter_id_bigint"
down_revision = "0009_media_resources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "media_chapters",
        "chapter_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "media_chapters",
        "chapter_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
