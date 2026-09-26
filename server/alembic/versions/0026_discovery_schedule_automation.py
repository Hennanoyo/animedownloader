"""store automation configuration with the discovery schedule

Revision ID: 0026_discovery_automation
Revises: 0025_discovery_configuration
Create Date: 2026-09-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0026_discovery_automation"
down_revision = "0025_discovery_configuration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "release_discovery_schedules",
        sa.Column("automation_mode", sa.String(length=16), nullable=False, server_default="off"),
    )
    op.add_column(
        "release_discovery_schedules",
        sa.Column(
            "automation_min_ranking_score",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "release_discovery_schedules",
        sa.Column(
            "automation_require_plan_match",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.execute(
        """
        INSERT INTO release_discovery_schedules (
            anime_id,
            automation_mode,
            automation_min_ranking_score,
            automation_require_plan_match
        )
        SELECT
            policies.anime_id,
            CASE
                WHEN policies.mode IN ('accept', 'download') THEN policies.mode
                WHEN policies.enabled THEN 'download'
                ELSE 'off'
            END,
            policies.min_ranking_score,
            policies.require_preference_match
        FROM anime_release_automation_policies AS policies
        WHERE NOT EXISTS (
            SELECT 1
            FROM release_discovery_schedules AS schedules
            WHERE schedules.anime_id = policies.anime_id
        )
        """
    )
    op.execute(
        """
        UPDATE release_discovery_schedules AS schedules
        SET
            automation_mode = CASE
                WHEN policies.mode IN ('accept', 'download') THEN policies.mode
                WHEN policies.enabled THEN 'download'
                ELSE 'off'
            END,
            automation_min_ranking_score = policies.min_ranking_score,
            automation_require_plan_match = policies.require_preference_match
        FROM anime_release_automation_policies AS policies
        WHERE policies.anime_id = schedules.anime_id
        """
    )


def downgrade() -> None:
    op.drop_column("release_discovery_schedules", "automation_require_plan_match")
    op.drop_column("release_discovery_schedules", "automation_min_ranking_score")
    op.drop_column("release_discovery_schedules", "automation_mode")