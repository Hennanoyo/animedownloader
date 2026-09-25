from __future__ import annotations

import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

from animedownloader_anime import Anime
from animedownloader_releases import (
    AnimeMatchCandidate,
    AnimeMatchResult,
    AnimeMatchStatus,
    ParsedRelease,
)


def canonicalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    parts: list[str] = []
    current: list[str] = []
    for character in normalized:
        if character.isalnum():
            current.append(character)
        elif current:
            parts.append("".join(current))
            current = []
    if current:
        parts.append("".join(current))
    return " ".join(parts)


class AnimeMatcher:
    def __init__(self, animes: Iterable[Anime]) -> None:
        self._index: dict[str, list[tuple[Anime, str]]] = defaultdict(list)
        for anime in animes:
            variants = (("title", anime.title), *anime.titles.items())
            seen: set[str] = set()
            for _key, title in variants:
                canonical = canonicalize_title(title)
                if not canonical or canonical in seen:
                    continue
                seen.add(canonical)
                self._index[canonical].append((anime, title))

    def match(self, parsed: ParsedRelease) -> AnimeMatchResult:
        normalized_series_title = (
            canonicalize_title(parsed.series_title)
            if parsed.series_title
            else None
        )
        if not normalized_series_title:
            return AnimeMatchResult(
                status=AnimeMatchStatus.UNMATCHED,
                normalized_series_title=None,
            )

        grouped: dict[UUID, tuple[Anime, list[str]]] = {}
        for anime, matched_title in self._index.get(normalized_series_title, []):
            entry = grouped.get(anime.id)
            if entry is None:
                grouped[anime.id] = (anime, [matched_title])
            elif matched_title not in entry[1]:
                entry[1].append(matched_title)

        candidates = tuple(
            AnimeMatchCandidate(
                anime_id=anime.id,
                title=anime.title,
                matched_titles=tuple(matched_titles),
            )
            for anime, matched_titles in grouped.values()
        )

        if len(candidates) == 1:
            status = AnimeMatchStatus.MATCHED
        elif candidates:
            status = AnimeMatchStatus.AMBIGUOUS
        else:
            status = AnimeMatchStatus.UNMATCHED

        return AnimeMatchResult(
            status=status,
            normalized_series_title=normalized_series_title,
            candidates=candidates,
        )
