"""create anime and episode tables

Revision ID: 0001_create_anime_episode
Revises:
Create Date: 2026-09-23
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_create_anime_episode"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "animes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("weekday", sa.String(length=16), nullable=False),
        sa.Column("air_time", sa.Time(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "episodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("anime_id", sa.Uuid(), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=256), nullable=True),
        sa.Column("source_title", sa.String(length=500), nullable=True),
        sa.Column("source_url", sa.String(length=2000), nullable=True),
        sa.Column("torrent_url", sa.String(length=2000), nullable=False),
        sa.Column("size", sa.String(length=64), nullable=True),
        sa.Column("seeders", sa.Integer(), nullable=True),
        sa.Column("leechers", sa.Integer(), nullable=True),
        sa.Column("downloads", sa.Integer(), nullable=True),
        sa.Column("info_hash", sa.String(length=128), nullable=True),
        sa.Column(
            "download_status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'not_started'"),
        ),
        sa.Column(
            "conversion_status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'not_started'"),
        ),
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
        sa.ForeignKeyConstraint(
            ["anime_id"],
            ["animes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "anime_id",
            "episode_number",
            name="uq_episodes_anime_number",
        ),
    )
    op.create_index(
        op.f("ix_episodes_anime_id"),
        "episodes",
        ["anime_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_episodes_anime_id"), table_name="episodes")
    op.drop_table("episodes")
    op.drop_table("animes")
