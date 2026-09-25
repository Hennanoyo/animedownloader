"""add structured anime title variants

Revision ID: 0017_anime_titles
Revises: 0016_release_search_profiles
Create Date: 2026-09-26
"""

from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

from alembic import op

revision = "0017_anime_titles"
down_revision = "0016_release_search_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "animes",
        sa.Column(
            "titles",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("animes", "titles")
