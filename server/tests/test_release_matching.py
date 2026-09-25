from uuid import uuid7

import pytest
from animedownloader_anime import Anime
from animedownloader_api.release_matching import AnimeMatcher, canonicalize_title
from animedownloader_releases import AnimeMatchStatus, ParsedRelease, ParseStatus


def _parsed(title: str | None) -> ParsedRelease:
    return ParsedRelease(
        provider_source="nyaa",
        source_id="release-1",
        original_title="raw",
        normalized_title="raw",
        release_group="ExampleSubs",
        series_title=title,
        episode_number=8,
        episode_title=None,
        season_number=None,
        resolution="1080p",
        source=None,
        video_codec="HEVC",
        audio_codec=None,
        bit_depth=10,
        status=ParseStatus.PARSED,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Frieren: Beyond Journey's End", "frieren beyond journey s end"),
        ("葬送のフリーレン", "葬送のフリーレン"),
        ("  SŌSŌ NO FRIEREN  ", "sōsō no frieren"),
    ],
)
def test_canonicalize_title(value: str, expected: str) -> None:
    assert canonicalize_title(value) == expected


def test_match_uses_main_and_alternate_titles() -> None:
    anime = Anime(
        id=uuid7(),
        title="Frieren: Beyond Journey's End",
        titles={"romaji": "Sousou no Frieren", "jp": "葬送のフリーレン"},
    )

    result = AnimeMatcher([anime]).match(_parsed("Sousou no Frieren"))

    assert result.status == AnimeMatchStatus.MATCHED
    assert len(result.candidates) == 1
    assert result.candidates[0].anime_id == anime.id
    assert result.candidates[0].matched_titles == ("Sousou no Frieren",)


def test_match_is_ambiguous_for_duplicate_canonical_titles() -> None:
    first = Anime(
        id=uuid7(),
        title="The Same Anime",
        titles={},
    )
    second = Anime(
        id=uuid7(),
        title="the-same-anime",
        titles={},
    )

    result = AnimeMatcher([first, second]).match(_parsed("The Same Anime"))

    assert result.status == AnimeMatchStatus.AMBIGUOUS
    assert {candidate.anime_id for candidate in result.candidates} == {
        first.id,
        second.id,
    }


def test_match_is_unmatched_for_unknown_title() -> None:
    anime = Anime(id=uuid7(), title="Frieren", titles={"romaji": "Sousou no Frieren"})

    result = AnimeMatcher([anime]).match(_parsed("Bocchi the Rock"))

    assert result.status == AnimeMatchStatus.UNMATCHED
    assert result.candidates == ()


def test_match_is_unmatched_without_series_title() -> None:
    anime = Anime(id=uuid7(), title="Frieren", titles={})

    result = AnimeMatcher([anime]).match(_parsed(None))

    assert result.status == AnimeMatchStatus.UNMATCHED
    assert result.normalized_series_title is None
