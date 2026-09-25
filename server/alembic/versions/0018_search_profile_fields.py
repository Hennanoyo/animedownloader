"""replace search templates with ordered search fields

Revision ID: 0018_search_profile_fields
Revises: 0017_anime_titles
Create Date: 2026-09-26
"""

import re
import uuid

import sqlalchemy as sa

from alembic import op

revision = "0018_search_profile_fields"
down_revision = "0017_anime_titles"
branch_labels = None
depends_on = None

_SEARCH_TOKEN_RE = re.compile(r"\{([a-z_]+)\}")
_ALLOWED_FIELDS = {"group", "title", "episode", "resolution", "codec"}
_DEFAULT_FIELDS = ("group", "title", "episode", "resolution", "codec")


def upgrade() -> None:
    op.create_table(
        "release_search_fields",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["release_search_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id",
            "priority",
            name="uq_release_search_fields_profile_priority",
        ),
    )
    op.create_index(
        "ix_release_search_fields_profile_id",
        "release_search_fields",
        ["profile_id"],
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT profile_id, priority, template "
            "FROM release_search_templates "
            "ORDER BY profile_id, priority"
        ),
    ).mappings().all()

    grouped: dict[object, list[str]] = {}
    for row in rows:
        fields = grouped.setdefault(row["profile_id"], [])
        for field in _SEARCH_TOKEN_RE.findall(row["template"]):
            if field in _ALLOWED_FIELDS and field not in fields:
                fields.append(field)

    profile_ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT id FROM release_search_profiles"),
        ).all()
    ]

    for profile_id in profile_ids:
        fields = grouped.get(profile_id) or list(_DEFAULT_FIELDS)
        for priority, field in enumerate(fields):
            bind.execute(
                sa.text(
                    """
                    INSERT INTO release_search_fields (id, profile_id, priority, field)
                    VALUES (:id, :profile_id, :priority, :field)
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "profile_id": profile_id,
                    "priority": priority,
                    "field": field,
                },
            )

    op.drop_table("release_search_templates")


def downgrade() -> None:
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

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT profile_id, priority, field "
            "FROM release_search_fields "
            "ORDER BY profile_id, priority"
        ),
    ).mappings().all()

    grouped: dict[object, list[str]] = {}
    for row in rows:
        grouped.setdefault(row["profile_id"], []).append(row["field"])

    for profile_id, fields in grouped.items():
        template = " ".join("{" + field + "}" for field in fields)
        bind.execute(
            sa.text(
                """
                INSERT INTO release_search_templates (id, profile_id, priority, template)
                VALUES (:id, :profile_id, 0, :template)
                """
            ),
            {
                "id": uuid.uuid4(),
                "profile_id": profile_id,
                "priority": 0,
                "template": template,
            },
        )

    op.drop_index(
        "ix_release_search_fields_profile_id",
        table_name="release_search_fields",
    )
    op.drop_table("release_search_fields")
