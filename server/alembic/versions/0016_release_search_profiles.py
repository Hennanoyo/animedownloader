"""add versioned release search profiles

Revision ID: 0016_release_search_profiles
Revises: 0015_release_parser_profiles
Create Date: 2026-09-25
"""

import sqlalchemy as sa

from alembic import op

revision = "0016_release_search_profiles"
down_revision = "0015_release_parser_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "release_search_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("release_group_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["release_group_id"],
            ["release_groups.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "release_group_id",
            "version",
            name="uq_release_search_profiles_group_version",
        ),
    )
    op.create_index(
        "ix_release_search_profiles_release_group_id",
        "release_search_profiles",
        ["release_group_id"],
    )
    op.create_index(
        "uq_release_search_profiles_group_active",
        "release_search_profiles",
        ["release_group_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "release_search_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("template", sa.String(length=300), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["release_search_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id",
            "priority",
            name="uq_release_search_templates_profile_priority",
        ),
    )
    op.create_index(
        "ix_release_search_templates_profile_id",
        "release_search_templates",
        ["profile_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_release_search_templates_profile_id",
        table_name="release_search_templates",
    )
    op.drop_table("release_search_templates")
    op.drop_index(
        "uq_release_search_profiles_group_active",
        table_name="release_search_profiles",
    )
    op.drop_index(
        "ix_release_search_profiles_release_group_id",
        table_name="release_search_profiles",
    )
    op.drop_table("release_search_profiles")
