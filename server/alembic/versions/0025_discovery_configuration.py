"""persist Discovery Search Plan settings and automation modes

Revision ID: 0025_discovery_configuration
Revises: 0024_discovery_query_diagnostics
Create Date: 2026-09-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0025_discovery_configuration"
down_revision = "0024_discovery_query_diagnostics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    plan_columns = (
        sa.Column("search_title_source", sa.String(length=16), nullable=True),
        sa.Column("search_title", sa.String(length=200), nullable=True),
        sa.Column("search_field_order", sa.JSON(), nullable=True),
        sa.Column("search_enabled_fields", sa.JSON(), nullable=True),
        sa.Column("search_group", sa.String(length=128), nullable=True),
        sa.Column("search_episode", sa.Integer(), nullable=True),
        sa.Column("search_resolution", sa.String(length=32), nullable=True),
        sa.Column("search_codec", sa.String(length=32), nullable=True),
        sa.Column("search_source", sa.String(length=32), nullable=True),
    )
    for column in plan_columns:
        op.add_column("release_discovery_schedules", column)

    op.add_column(
        "anime_release_automation_policies",
        sa.Column("mode", sa.String(length=16), nullable=True),
    )
    op.execute(
        """
        UPDATE anime_release_automation_policies
        SET mode = CASE
            WHEN enabled THEN 'download'
            ELSE 'off'
        END
        """
    )
    op.alter_column(
        "anime_release_automation_policies",
        "mode",
        existing_type=sa.String(length=16),
        nullable=False,
        server_default="off",
    )


def downgrade() -> None:
    op.alter_column(
        "anime_release_automation_policies",
        "mode",
        existing_type=sa.String(length=16),
        server_default=None,
        nullable=True,
    )
    op.drop_column("anime_release_automation_policies", "mode")
    for column_name in (
        "search_source",
        "search_codec",
        "search_resolution",
        "search_episode",
        "search_group",
        "search_enabled_fields",
        "search_field_order",
        "search_title",
        "search_title_source",
    ):
        op.drop_column("release_discovery_schedules", column_name)
