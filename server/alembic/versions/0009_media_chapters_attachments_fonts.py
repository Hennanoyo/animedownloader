"""add media chapters, attachments, and reusable fonts

Revision ID: 0009_media_resources
Revises: 0008_subtitle_processing
Create Date: 2026-09-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_media_resources"
down_revision = "0008_subtitle_processing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column("chapters_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("attachments_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("attachments_processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "media_chapters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("media_asset_id", sa.UUID(), nullable=False),
        sa.Column("chapter_index", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("start_time_seconds", sa.Float(), nullable=False),
        sa.Column("end_time_seconds", sa.Float(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "media_asset_id",
            "chapter_index",
            name="uq_media_chapters_asset_index",
        ),
    )
    op.create_index(
        "ix_media_chapters_media_asset_id",
        "media_chapters",
        ["media_asset_id"],
    )

    op.create_table(
        "media_fonts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("path", sa.String(length=2000), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha256", name="uq_media_fonts_sha256"),
    )
    op.create_index("ix_media_fonts_sha256", "media_fonts", ["sha256"])

    op.create_table(
        "media_attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("media_asset_id", sa.UUID(), nullable=False),
        sa.Column("attachment_index", sa.Integer(), nullable=False),
        sa.Column("stream_index", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=True),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("is_font", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("extracted_path", sa.String(length=2000), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("font_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["font_id"], ["media_fonts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "media_asset_id",
            "attachment_index",
            name="uq_media_attachments_asset_index",
        ),
    )
    op.create_index("ix_media_attachments_media_asset_id", "media_attachments", ["media_asset_id"])
    op.create_index("ix_media_attachments_font_id", "media_attachments", ["font_id"])


def downgrade() -> None:
    op.drop_index("ix_media_attachments_font_id", table_name="media_attachments")
    op.drop_index("ix_media_attachments_media_asset_id", table_name="media_attachments")
    op.drop_table("media_attachments")
    op.drop_index("ix_media_fonts_sha256", table_name="media_fonts")
    op.drop_table("media_fonts")
    op.drop_index("ix_media_chapters_media_asset_id", table_name="media_chapters")
    op.drop_table("media_chapters")
    op.drop_column("media_assets", "attachments_processed_at")
    op.drop_column("media_assets", "attachments_updated_at")
    op.drop_column("media_assets", "chapters_updated_at")
