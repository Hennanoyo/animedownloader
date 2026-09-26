"""add per-anime release preferences

Revision ID: 0021_anime_release_preferences
Revises: 0020_episode_release_group
Create Date: 2026-09-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0021_anime_release_preferences"
down_revision = "0020_episode_release_group"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anime_release_preferences",
        sa.Column("anime_id", sa.UUID(), nullable=False),
        sa.Column("release_group_id", sa.UUID(), nullable=True),
        sa.Column("resolution", sa.String(length=32), nullable=True),
        sa.Column("video_codec", sa.String(length=32), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["anime_id"],
            ["animes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["release_group_id"],
            ["release_groups.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("anime_id"),
    )
    op.create_index(
        "ix_anime_release_preferences_release_group_id",
        "anime_release_preferences",
        ["release_group_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_anime_release_preferences_release_group_id",
        table_name="anime_release_preferences",
    )
    op.drop_table("anime_release_preferences")
