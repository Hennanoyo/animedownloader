"""persist periodic release discovery candidates

Revision ID: 0022_release_discovery_candidates
Revises: 0021_anime_release_preferences
Create Date: 2026-09-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0022_release_discovery_candidates"
down_revision = "0021_anime_release_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "release_discovery_schedules",
        sa.Column("anime_id", sa.UUID(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="360"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["anime_id"], ["animes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("anime_id"),
    )

    op.create_table(
        "release_discovery_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("anime_id", sa.UUID(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("query", sa.String(length=500), nullable=True),
        sa.Column("search_profile_version", sa.Integer(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["anime_id"], ["animes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "anime_id",
            "scheduled_for",
            name="uq_release_discovery_runs_anime_scheduled_for",
        ),
    )
    op.create_index(
        "ix_release_discovery_runs_anime_id",
        "release_discovery_runs",
        ["anime_id"],
    )

    op.create_table(
        "release_discovery_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("anime_id", sa.UUID(), nullable=False),
        sa.Column("last_run_id", sa.UUID(), nullable=True),
        sa.Column("provider_source", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=256), nullable=False),
        sa.Column("source_title", sa.String(length=500), nullable=False),
        sa.Column("page_url", sa.String(length=2000), nullable=False),
        sa.Column("torrent_url", sa.String(length=2000), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("size", sa.String(length=64), nullable=True),
        sa.Column("seeders", sa.Integer(), nullable=True),
        sa.Column("leechers", sa.Integer(), nullable=True),
        sa.Column("downloads", sa.Integer(), nullable=True),
        sa.Column("info_hash", sa.String(length=128), nullable=True),
        sa.Column("normalized_title", sa.String(length=500), nullable=False),
        sa.Column("release_group", sa.String(length=128), nullable=True),
        sa.Column("series_title", sa.String(length=300), nullable=True),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("episode_title", sa.String(length=300), nullable=True),
        sa.Column("season_number", sa.Integer(), nullable=True),
        sa.Column("resolution", sa.String(length=32), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("video_codec", sa.String(length=32), nullable=True),
        sa.Column("audio_codec", sa.String(length=32), nullable=True),
        sa.Column("bit_depth", sa.Integer(), nullable=True),
        sa.Column("parse_status", sa.String(length=16), nullable=False),
        sa.Column("parse_warnings", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("failed_required_fields", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("parser_profile_version", sa.Integer(), nullable=True),
        sa.Column("normalized_series_title", sa.String(length=300), nullable=True),
        sa.Column("match_status", sa.String(length=16), nullable=False),
        sa.Column("match_candidates", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("ranking_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ranking_reasons", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="new"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["anime_id"], ["animes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_run_id"], ["release_discovery_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "anime_id",
            "provider_source",
            "source_id",
            name="uq_release_discovery_candidates_identity",
        ),
    )
    op.create_index(
        "ix_release_discovery_candidates_anime_id",
        "release_discovery_candidates",
        ["anime_id"],
    )
    op.create_index(
        "ix_release_discovery_candidates_last_run_id",
        "release_discovery_candidates",
        ["last_run_id"],
    )
    op.create_index(
        "ix_release_discovery_candidates_status",
        "release_discovery_candidates",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_release_discovery_candidates_status",
        table_name="release_discovery_candidates",
    )
    op.drop_index(
        "ix_release_discovery_candidates_last_run_id",
        table_name="release_discovery_candidates",
    )
    op.drop_index(
        "ix_release_discovery_candidates_anime_id",
        table_name="release_discovery_candidates",
    )
    op.drop_table("release_discovery_candidates")
    op.drop_index(
        "ix_release_discovery_runs_anime_id",
        table_name="release_discovery_runs",
    )
    op.drop_table("release_discovery_runs")
    op.drop_table("release_discovery_schedules")
