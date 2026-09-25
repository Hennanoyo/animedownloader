"""add release parser operational samples and health

Revision ID: 0019_release_parser_operations
Revises: 0018_search_profile_fields
Create Date: 2026-09-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0019_release_parser_operations"
down_revision = "0018_search_profile_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "release_parser_samples",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("release_group_id", sa.UUID(), nullable=False),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="nyaa",
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
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
            ["release_group_id"],
            ["release_groups.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_release_parser_samples_release_group_id",
        "release_parser_samples",
        ["release_group_id"],
    )

    op.create_table(
        "release_parser_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("release_group_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="nyaa",
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "failed_required_fields",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["release_group_id"],
            ["release_groups.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["release_parser_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_release_parser_observations_release_group_id",
        "release_parser_observations",
        ["release_group_id"],
    )
    op.create_index(
        "ix_release_parser_observations_profile_id",
        "release_parser_observations",
        ["profile_id"],
    )
    op.create_index(
        "ix_release_parser_observations_observed_at",
        "release_parser_observations",
        ["observed_at"],
    )

    op.create_table(
        "release_parser_health",
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parsed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ambiguous_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unparsed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unsupported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["release_parser_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("profile_id"),
    )


def downgrade() -> None:
    op.drop_table("release_parser_health")
    op.drop_index(
        "ix_release_parser_observations_observed_at",
        table_name="release_parser_observations",
    )
    op.drop_index(
        "ix_release_parser_observations_profile_id",
        table_name="release_parser_observations",
    )
    op.drop_index(
        "ix_release_parser_observations_release_group_id",
        table_name="release_parser_observations",
    )
    op.drop_table("release_parser_observations")
    op.drop_index(
        "ix_release_parser_samples_release_group_id",
        table_name="release_parser_samples",
    )
    op.drop_table("release_parser_samples")
