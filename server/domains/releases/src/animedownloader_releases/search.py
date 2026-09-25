from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Final

from .models import Release, SearchField, SearchProfileSpec, SearchQueryContext

MAX_SEARCH_TEMPLATE_LENGTH: Final = 300
MAX_SEARCH_TEMPLATES: Final = 16

_SEARCH_TOKEN_RE = re.compile(r"\{([a-z_]+)\}")
_ALLOWED_SEARCH_FIELDS: Final[frozenset[str]] = frozenset(
    field.value for field in SearchField
)
DEFAULT_SEARCH_TEMPLATES: Final[tuple[str, ...]] = (
    "{group} {title} {episode}",
    "{title} {episode}",
    "{group} {title}",
    "{title}",
)


def normalize_release_group_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    normalized = re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE)
    return normalized.strip("-")


def validate_search_template(template: str) -> tuple[str, ...]:
    if not template.strip():
        return ("template must not be empty",)
    if len(template) > MAX_SEARCH_TEMPLATE_LENGTH:
        return (
            f"template exceeds {MAX_SEARCH_TEMPLATE_LENGTH} characters",
        )

    errors: list[str] = []
    tokens = _SEARCH_TOKEN_RE.findall(template)
    for token in tokens:
        if token not in _ALLOWED_SEARCH_FIELDS:
            errors.append(f"unsupported search field: {token}")

    remainder = _SEARCH_TOKEN_RE.sub("", template)
    if "{" in remainder or "}" in remainder:
        errors.append("template contains an invalid placeholder")

    return tuple(errors)


def validate_search_profile(profile: SearchProfileSpec) -> tuple[str, ...]:
    if profile.version < 1:
        raise ValueError("search profile version must be >= 1")
    if not profile.release_group.strip():
        raise ValueError("release group must not be empty")
    if not profile.templates:
        raise ValueError("at least one search template is required")
    if len(profile.templates) > MAX_SEARCH_TEMPLATES:
        raise ValueError(
            f"search profile exceeds {MAX_SEARCH_TEMPLATES} templates",
        )

    priorities: set[int] = set()
    errors: list[str] = []
    for item in profile.templates:
        if item.priority < 0:
            errors.append(f"priority {item.priority}: priority must be >= 0")
        for error in validate_search_template(item.template):
            errors.append(f"priority {item.priority}: {error}")
        if item.priority in priorities:
            errors.append(f"duplicate template priority: {item.priority}")
        priorities.add(item.priority)

    return tuple(errors)


def build_search_queries(
    context: SearchQueryContext,
    profile: SearchProfileSpec | None = None,
) -> tuple[str, ...]:
    if profile is None:
        templates = tuple(
            SearchTemplateSpec(template=template, priority=index)
            for index, template in enumerate(DEFAULT_SEARCH_TEMPLATES)
        )
    else:
        errors = validate_search_profile(profile)
        if errors:
            raise ValueError("; ".join(errors))
        templates = profile.templates

    values = {
        SearchField.GROUP.value: _clean_value(context.group),
        SearchField.TITLE.value: _clean_value(context.title),
        SearchField.EPISODE.value: (
            str(context.episode) if context.episode is not None else None
        ),
        SearchField.RESOLUTION.value: _clean_value(context.resolution),
        SearchField.CODEC.value: _clean_value(context.codec),
    }

    queries: list[str] = []
    seen: set[str] = set()
    for item in sorted(templates, key=lambda value: value.priority):
        query = _render_template(item.template, values)
        if query is None:
            continue
        key = query.casefold()
        if key in seen:
            continue
        seen.add(key)
        queries.append(query)

    return tuple(queries)


def merge_releases(results: Iterable[Iterable[Release]]) -> tuple[Release, ...]:
    merged: list[Release] = []
    seen_source_ids: set[tuple[str, str]] = set()
    seen_hashes: set[str] = set()

    for releases in results:
        for release in releases:
            source_id = (
                release.source.casefold(),
                release.id,
            ) if release.source and release.id else None
            info_hash = release.info_hash.casefold() if release.info_hash else None
            if source_id is not None and source_id in seen_source_ids:
                continue
            if info_hash is not None and info_hash in seen_hashes:
                continue
            if source_id is not None:
                seen_source_ids.add(source_id)
            if info_hash is not None:
                seen_hashes.add(info_hash)
            merged.append(release)

    return tuple(merged)


def _render_template(
    template: str,
    values: dict[str, str | None],
) -> str | None:
    rendered = _SEARCH_TOKEN_RE.sub(
        lambda match: values.get(match.group(1)) or "",
        template,
    )
    rendered = re.sub(r"\s+", " ", rendered).strip()
    rendered = re.sub(r"\s+([,._-])", r"\1", rendered)
    rendered = re.sub(r"([,._-])\s+", r"\1 ", rendered)
    return rendered or None


def _clean_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).strip()
    return normalized or None
