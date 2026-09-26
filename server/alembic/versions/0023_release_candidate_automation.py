"""add policy-controlled release candidate automation

Revision ID: 0023_candidate_automation
Revises: 0022_release_candidates
Create Date: 2026-09-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0023_candidate_automation"
down_revision = "0022_release_candidates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anime_release_automation_policies",
        sa.Column("anime_id", sa.UUID(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("min_ranking_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "require_preference_match",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
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
        sa.CheckConstraint(
            "min_ranking_score >= 0",
            name="ck_anime_release_automation_policies_min_score_nonnegative",
        ),
        sa.ForeignKeyConstraint(["anime_id"], ["animes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("anime_id"),
    )

    op.add_column(
        "release_discovery_candidates",
        sa.Column(
            "automation_status",
            sa.String(length=16),
            nullable=False,
            server_default="idle",
        ),
    )
    op.add_column(
        "release_discovery_candidates",
        sa.Column("automation_claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "release_discovery_candidates",
        sa.Column("automation_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "release_discovery_candidates",
        sa.Column("automation_error", sa.String(length=2000), nullable=True),
    )
    op.create_index(
        "ix_release_discovery_candidates_automation_status",
        "release_discovery_candidates",
        ["automation_status"],
    )
    op.create_index(
        "ix_release_discovery_candidates_automation_claimed_at",
        "release_discovery_candidates",
        ["automation_claimed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_release_discovery_candidates_automation_claimed_at",
        table_name="release_discovery_candidates",
    )
    op.drop_index(
        "ix_release_discovery_candidates_automation_status",
        table_name="release_discovery_candidates",
    )
    op.drop_column("release_discovery_candidates", "automation_error")
    op.drop_column("release_discovery_candidates", "automation_completed_at")
    op.drop_column("release_discovery_candidates", "automation_claimed_at")
    op.drop_column("release_discovery_candidates", "automation_status")
    op.drop_table("anime_release_automation_policies")
