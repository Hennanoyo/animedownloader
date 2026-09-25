from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Final

from .models import (
    Release,
    SearchField,
    SearchProfileSpec,
    SearchQueryContext,
)

MAX_SEARCH_FIELDS: Final = len(SearchField)
DEFAULT_SEARCH_FIELDS: Final[tuple[SearchField, ...]] = (
    SearchField.GROUP,
    SearchField.TITLE,
    SearchField.EPISODE,
    SearchField.RESOLUTION,
    SearchField.CODEC,
)


def normalize_release_group_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    normalized = re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE)
    return normalized.strip("-")


def validate_search_profile(profile: SearchProfileSpec) -> tuple[str, ...]:
    if profile.version < 1:
        raise ValueError("search profile version must be >= 1")
    if not profile.release_group.strip():
        raise ValueError("release group must not be empty")
    if not profile.fields:
        raise ValueError("at least one search field is required")
    if len(profile.fields) > MAX_SEARCH_FIELDS:
        raise ValueError(
            f"search profile exceeds {MAX_SEARCH_FIELDS} fields",
        )
    if len(set(profile.fields)) != len(profile.fields):
        return ("duplicate search field",)
    return ()


def build_search_query(
    context: SearchQueryContext,
    profile: SearchProfileSpec | None = None,
    fields: tuple[SearchField, ...] | None = None,
) -> str | None:
    selected_fields = (
        fields
        if fields is not None
        else profile.fields if profile is not None else DEFAULT_SEARCH_FIELDS
    )
    if not selected_fields:
        return None
    if len(selected_fields) > MAX_SEARCH_FIELDS:
        raise ValueError(f"search query exceeds {MAX_SEARCH_FIELDS} fields")
    if len(set(selected_fields)) != len(selected_fields):
        raise ValueError("duplicate search field")

    values = {
        SearchField.GROUP: _clean_value(context.group),
        SearchField.TITLE: _clean_value(context.title),
        SearchField.EPISODE: (
            str(context.episode) if context.episode is not None else None
        ),
        SearchField.RESOLUTION: _clean_value(context.resolution),
        SearchField.CODEC: _clean_value(context.codec),
    }
    rendered = " ".join(
        value for field in selected_fields if (value := values.get(field))
    )
    return _clean_value(rendered)


def merge_releases(results: Iterable[Iterable[Release]]) -> tuple[Release, ...]:
    merged: list[Release] = []
    seen_source_ids: set[tuple[str, str]] = set()
    seen_source_titles: set[tuple[str, str]] = set()
    seen_hashes: set[str] = set()

    for releases in results:
        for release in releases:
            source = release.source.strip().casefold()
            source_id = (source, release.id.strip()) if source and release.id.strip() else None
            info_hash = release.info_hash.strip().casefold() if release.info_hash else None
            title_key = _normalize_release_title(release.title)

            if source_id is not None and source_id in seen_source_ids:
                continue
            if info_hash is not None and info_hash in seen_hashes:
                continue
            if info_hash is None and source and title_key:
                source_title = (source, title_key)
                if source_title in seen_source_titles:
                    continue

            if source_id is not None:
                seen_source_ids.add(source_id)
            if info_hash is not None:
                seen_hashes.add(info_hash)
            if info_hash is None and source and title_key:
                seen_source_titles.add((source, title_key))
            merged.append(release)

    return tuple(merged)


def _normalize_release_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def _clean_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).strip()
    return normalized or None
