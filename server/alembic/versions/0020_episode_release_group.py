"""persist episode release group provenance

Revision ID: 0020_episode_release_group
Revises: 0019_release_parser_operations
Create Date: 2026-09-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0020_episode_release_group"
down_revision = "0019_release_parser_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "episodes",
        sa.Column("release_group_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_episodes_release_group_id",
        "episodes",
        "release_groups",
        ["release_group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_episodes_release_group_id",
        "episodes",
        ["release_group_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_episodes_release_group_id",
        table_name="episodes",
    )
    op.drop_constraint(
        "fk_episodes_release_group_id",
        "episodes",
        type_="foreignkey",
    )
    op.drop_column("episodes", "release_group_id")
