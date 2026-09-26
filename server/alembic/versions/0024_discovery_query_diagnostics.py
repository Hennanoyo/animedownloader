"""persist per-query release discovery diagnostics

Revision ID: 0024_discovery_query_diagnostics
Revises: 0023_candidate_automation
Create Date: 2026-09-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0024_discovery_query_diagnostics"
down_revision = "0023_candidate_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "release_discovery_queries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "result_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "result_cap_reached",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["release_discovery_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "position",
            name="uq_release_discovery_queries_run_position",
        ),
    )
    op.create_index(
        "ix_release_discovery_queries_run_id",
        "release_discovery_queries",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_release_discovery_queries_run_id",
        table_name="release_discovery_queries",
    )
    op.drop_table("release_discovery_queries")
