from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

_EXTENSION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _normalize_extension(value: str) -> str:
    extension = value.strip().lstrip(".").casefold()
    if not _EXTENSION_PATTERN.fullmatch(extension):
        raise ValueError(f"Invalid artifact extension: {value!r}")
    return extension


def _validate_sha256(value: str) -> str:
    sha256 = value.strip().casefold()
    if not _SHA256_PATTERN.fullmatch(sha256):
        raise ValueError("SHA-256 must be a 64-character hexadecimal string")
    return sha256


def _relative_key(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Invalid relative storage key: {value!r}")
    return path.as_posix()


class PlayableArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_id: UUID
    variant_id: UUID
    extension: str = "mp4"

    _normalize_extension = field_validator("extension")(_normalize_extension)

    @computed_field
    @property
    def filename(self) -> str:
        return f"{self.variant_id}.{self.extension}"

    @computed_field
    @property
    def object_key(self) -> str:
        return f"playable/{self.asset_id}/{self.filename}"


class SubtitleArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_id: UUID
    track_id: UUID
    extension: str

    _normalize_extension = field_validator("extension")(_normalize_extension)

    @computed_field
    @property
    def filename(self) -> str:
        return f"{self.track_id}.{self.extension}"

    @computed_field
    @property
    def object_key(self) -> str:
        return f"subtitles/{self.asset_id}/{self.filename}"


class AttachmentArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_id: UUID
    attachment_id: UUID
    extension: str

    _normalize_extension = field_validator("extension")(_normalize_extension)

    @computed_field
    @property
    def filename(self) -> str:
        return f"{self.attachment_id}.{self.extension}"

    @computed_field
    @property
    def object_key(self) -> str:
        return f"attachments/{self.asset_id}/{self.filename}"


class FontArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    sha256: str
    extension: str

    _validate_sha256 = field_validator("sha256")(_validate_sha256)
    _normalize_extension = field_validator("extension")(_normalize_extension)

    @computed_field
    @property
    def filename(self) -> str:
        return f"{self.sha256}.{self.extension}"

    @computed_field
    @property
    def object_key(self) -> str:
        return f"fonts/{self.sha256[:2]}/{self.filename}"


class ThumbnailArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_id: UUID
    kind: Literal["sprite", "vtt"]

    @computed_field
    @property
    def filename(self) -> str:
        return f"sprite.{self.kind}"

    @computed_field
    @property
    def object_key(self) -> str:
        return f"thumbnails/{self.asset_id}/{self.filename}"


class StreamingPackageArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    package_id: UUID

    @computed_field
    @property
    def object_prefix(self) -> str:
        return f"streaming/{self.package_id}"

    @computed_field
    @property
    def master_playlist_key(self) -> str:
        return f"{self.object_prefix}/master.m3u8"

    @computed_field
    @property
    def dash_manifest_key(self) -> str:
        return f"{self.object_prefix}/manifest.mpd"

    def representation_key(self, quality: str, filename: str) -> str:
        quality_key = _relative_key(quality)
        filename_key = _relative_key(filename)
        return f"{self.object_prefix}/{quality_key}/{filename_key}"

    def segment_key(self, quality: str, segment_filename: str) -> str:
        return self.representation_key(quality, f"s/{segment_filename}")
