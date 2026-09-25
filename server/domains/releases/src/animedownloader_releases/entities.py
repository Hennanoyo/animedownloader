from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from animedownloader_database import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ParserProfileStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class ReleaseGroup(Base):
    __tablename__ = "release_groups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(128), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true", default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    parser_profiles: Mapped[list[ReleaseParserProfile]] = relationship(
        back_populates="release_group",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ReleaseParserProfile.version",
    )
    search_profiles: Mapped[list[ReleaseSearchProfile]] = relationship(
        back_populates="release_group",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ReleaseSearchProfile.version",
    )


class ReleaseParserProfile(Base):
    __tablename__ = "release_parser_profiles"
    __table_args__ = (
        UniqueConstraint(
            "release_group_id",
            "version",
            name="uq_release_parser_profiles_group_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    release_group_id: Mapped[UUID] = mapped_column(
        ForeignKey("release_groups.id", ondelete="CASCADE"),
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(16),
        default=ParserProfileStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    release_group: Mapped[ReleaseGroup] = relationship(back_populates="parser_profiles")
    rules: Mapped[list[ReleaseParserRule]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ReleaseParserRule.priority",
    )


class ReleaseParserRule(Base):
    __tablename__ = "release_parser_rules"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "priority",
            name="uq_release_parser_rules_profile_priority",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("release_parser_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    field: Mapped[str] = mapped_column(String(64))
    pattern: Mapped[str] = mapped_column(String(2000))
    priority: Mapped[int] = mapped_column(Integer)
    required: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    flags: Mapped[str] = mapped_column(String(32), server_default="", default="")
    transform: Mapped[str] = mapped_column(String(32), default="identity")

    profile: Mapped[ReleaseParserProfile] = relationship(back_populates="rules")


class SearchProfileStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class ReleaseSearchProfile(Base):
    __tablename__ = "release_search_profiles"
    __table_args__ = (
        UniqueConstraint(
            "release_group_id",
            "version",
            name="uq_release_search_profiles_group_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    release_group_id: Mapped[UUID] = mapped_column(
        ForeignKey("release_groups.id", ondelete="CASCADE"),
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(16),
        default=SearchProfileStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    release_group: Mapped[ReleaseGroup] = relationship(
        back_populates="search_profiles",
    )
    fields: Mapped[list[ReleaseSearchField]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ReleaseSearchField.priority",
    )


class ReleaseSearchField(Base):
    __tablename__ = "release_search_fields"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "priority",
            name="uq_release_search_templates_profile_priority",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("release_search_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer)
    field: Mapped[str] = mapped_column(String(32))

    profile: Mapped[ReleaseSearchProfile] = relationship(
        back_populates="fields",
    )
