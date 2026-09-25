"""add versioned release parser profiles

Revision ID: 0015_release_parser_profiles
Revises: 0014_media_packaging
Create Date: 2026-09-25
"""

import sqlalchemy as sa

from alembic import op

revision = "0015_release_parser_profiles"
down_revision = "0014_media_packaging"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "release_groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_release_groups_name", "release_groups", ["name"])

    op.create_table(
        "release_parser_profiles",
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
        sa.Column(
            "activated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["release_group_id"],
            ["release_groups.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "release_group_id",
            "version",
            name="uq_release_parser_profiles_group_version",
        ),
    )
    op.create_index(
        "ix_release_parser_profiles_release_group_id",
        "release_parser_profiles",
        ["release_group_id"],
    )
    op.create_index(
        "uq_release_parser_profiles_group_active",
        "release_parser_profiles",
        ["release_group_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "release_parser_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("field", sa.String(length=64), nullable=False),
        sa.Column("pattern", sa.String(length=2000), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("flags", sa.String(length=32), server_default="", nullable=False),
        sa.Column("transform", sa.String(length=32), server_default="identity", nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["release_parser_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id",
            "priority",
            name="uq_release_parser_rules_profile_priority",
        ),
    )
    op.create_index(
        "ix_release_parser_rules_profile_id",
        "release_parser_rules",
        ["profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_release_parser_rules_profile_id", table_name="release_parser_rules")
    op.drop_table("release_parser_rules")
    op.drop_index(
        "uq_release_parser_profiles_group_active",
        table_name="release_parser_profiles",
    )
    op.drop_index(
        "ix_release_parser_profiles_release_group_id",
        table_name="release_parser_profiles",
    )
    op.drop_table("release_parser_profiles")
    op.drop_index("ix_release_groups_name", table_name="release_groups")
    op.drop_table("release_groups")
