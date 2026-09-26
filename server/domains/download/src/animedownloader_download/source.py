from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from uuid import UUID

MEDIA_EXTENSIONS = frozenset(
    {
        ".avi",
        ".flv",
        ".m2ts",
        ".m4v",
        ".mkv",
        ".mov",
        ".mp4",
        ".mpeg",
        ".mpg",
        ".mts",
        ".ts",
        ".webm",
        ".wmv",
    }
)


class MediaSourceStatus(StrEnum):
    FOUND = "found"
    MISSING_DIRECTORY = "missing_directory"
    NO_MEDIA = "no_media"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class MediaSourceResolution:
    status: MediaSourceStatus
    root: Path
    path: Path | None = None
    candidates: tuple[Path, ...] = ()

    @property
    def is_ready(self) -> bool:
        return self.status is MediaSourceStatus.FOUND and self.path is not None


def resolve_media_source(root: Path) -> MediaSourceResolution:
    if not root.is_dir():
        return MediaSourceResolution(
            status=MediaSourceStatus.MISSING_DIRECTORY,
            root=root,
        )

    candidates: tuple[Path, ...] = tuple(
        sorted(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.casefold() in MEDIA_EXTENSIONS
        )
    )

    if not candidates:
        return MediaSourceResolution(
            status=MediaSourceStatus.NO_MEDIA,
            root=root,
        )

    if len(candidates) > 1:
        return MediaSourceResolution(
            status=MediaSourceStatus.AMBIGUOUS,
            root=root,
            candidates=candidates,
        )

    return MediaSourceResolution(
        status=MediaSourceStatus.FOUND,
        root=root,
        path=next(iter(candidates)),
        candidates=candidates,
    )


def resolve_selected_media_source(root: Path, relative_path: str) -> Path | None:
    candidate = (root / relative_path).resolve()
    root_resolved = root.resolve()

    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None

    if (
        not candidate.is_file()
        or candidate.suffix.casefold() not in MEDIA_EXTENSIONS
    ):
        return None

    return candidate


def relative_media_source(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def find_download_directories(root: Path) -> tuple[Path, ...]:
    if not root.is_dir():
        return ()

    return tuple(
        sorted(
            path
            for path in root.iterdir()
            if path.is_dir() and _is_uuid_directory(path.name)
        )
    )


def describe_media_source(resolution: MediaSourceResolution) -> str:
    if resolution.status is MediaSourceStatus.MISSING_DIRECTORY:
        return f"Download directory does not exist: {resolution.root}"

    if resolution.status is MediaSourceStatus.NO_MEDIA:
        return f"No supported media file found in download directory: {resolution.root}"

    if resolution.status is MediaSourceStatus.AMBIGUOUS:
        names = ", ".join(
            relative_media_source(resolution.root, path)
            for path in resolution.candidates[:5]
        )
        suffix = " ..." if len(resolution.candidates) > 5 else ""
        return (
            f"Expected exactly one media file in {resolution.root}, "
            f"found {len(resolution.candidates)}: {names}{suffix}"
        )

    if resolution.path is None:
        return f"Media source resolution returned no path: {resolution.root}"

    return str(resolution.path)


def _is_uuid_directory(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True
