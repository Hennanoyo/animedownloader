from dataclasses import replace

import pytest
from animedownloader_releases import (
    ParserField,
    ParserProfileSpec,
    ParserRuleSpec,
    ParserTransform,
    ParseStatus,
    Release,
    normalize_release_title,
    parse_release,
    validate_parser_profile,
    validate_parser_samples,
)


def _release(title: str) -> Release:
    return Release(
        source="nyaa",
        id=f"https://nyaa.si/view/{abs(hash(title))}",
        title=title,
        page_url="https://nyaa.si/view/example",
        torrent_url="https://nyaa.si/download/example.torrent",
        published_at=None,
        size="1 GiB",
        seeders=10,
        leechers=1,
        downloads=2,
        info_hash=None,
    )


@pytest.mark.parametrize(
    ("title", "expected_group", "expected_series", "expected_episode"),
    [
        (
            "[ExampleSubs] Frieren - 01 [1080p].mkv",
            "ExampleSubs",
            "Frieren",
            1,
        ),
        (
            "[ExampleSubs] Frieren - 01 - The Journey [1080p].mkv",
            "ExampleSubs",
            "Frieren",
            1,
        ),
        (
            "[ExampleSubs] Frieren S01E02 [1080p].mkv",
            "ExampleSubs",
            "Frieren",
            2,
        ),
        (
            "[ExampleSubs] Frieren - 2026 - 03 [1080p].mkv",
            "ExampleSubs",
            "Frieren - 2026",
            3,
        ),
    ],
)
def test_generic_parser_extracts_common_episode_forms(
    title: str,
    expected_group: str,
    expected_series: str,
    expected_episode: int,
) -> None:
    parsed = parse_release(_release(title))

    assert parsed.status == ParseStatus.PARSED
    assert parsed.release_group == expected_group
    assert parsed.series_title == expected_series
    assert parsed.episode_number == expected_episode


def test_generic_parser_preserves_episode_position_around_technical_metadata() -> None:
    parsed = parse_release(
        _release("[ExampleSubs] Frieren [1080p] - 03 [HEVC].mkv")
    )

    assert parsed.status == ParseStatus.PARSED
    assert parsed.series_title == "Frieren"
    assert parsed.episode_number == 3


def test_generic_parser_extracts_technical_metadata() -> None:
    parsed = parse_release(
        _release("[ExampleSubs] Frieren - 03 [1080p][HEVC][10bit][WEB-DL].mkv")
    )

    assert parsed.resolution == "1080p"
    assert parsed.video_codec == "HEVC"
    assert parsed.bit_depth == 10
    assert parsed.source == "WEB-DL"


@pytest.mark.parametrize(
    "title",
    [
        "[ExampleSubs] Frieren [Batch].mkv",
        "[ExampleSubs] Frieren - 01 - 02 [1080p].mkv",
        "[ExampleSubs] Frieren - Movie [1080p].mkv",
    ],
)
def test_generic_parser_does_not_guess_unsupported_episode_forms(title: str) -> None:
    parsed = parse_release(_release(title))

    assert parsed.episode_number is None
    assert parsed.status in {ParseStatus.AMBIGUOUS, ParseStatus.UNPARSED}


def test_generic_parser_marks_multiple_numbers_ambiguous() -> None:
    parsed = parse_release(_release("[ExampleSubs] Anime 12 13 [1080p].mkv"))

    assert parsed.status == ParseStatus.AMBIGUOUS
    assert parsed.episode_number is None


def test_normalize_release_title_removes_known_media_extension() -> None:
    assert normalize_release_title("[Group] Anime - 01.mkv") == "[Group] Anime - 01"


def test_parser_profile_overrides_generic_fields() -> None:
    profile = ParserProfileSpec(
        release_group="ExampleSubs",
        version=2,
        rules=(
            ParserRuleSpec(
                field=ParserField.SERIES_TITLE,
                pattern=r"\[(?P<series_title>ExampleSubs)\]\s+(?P<title>[^-]+)\s+-\s+\d+",
                priority=10,
                transform=ParserTransform.STRIP,
            ),
            ParserRuleSpec(
                field=ParserField.EPISODE_NUMBER,
                pattern=r"Episode-(?P<episode_number>\d{2})",
                priority=20,
                transform=ParserTransform.TO_INT,
            ),
        ),
    )

    release = replace(_release("[ExampleSubs] Frieren Episode-08 [1080p].mkv"))
    parsed = parse_release(release, profile)

    assert parsed.parser_profile_version == 2
    assert parsed.series_title == "Frieren"
    assert parsed.episode_number == 8
    assert parsed.status == ParseStatus.PARSED


def test_parser_profile_validation_requires_unique_priorities() -> None:
    profile = ParserProfileSpec(
        release_group="ExampleSubs",
        version=1,
        rules=(
            ParserRuleSpec(
                field=ParserField.EPISODE_NUMBER,
                pattern=r"(?P<episode_number>\d+)",
                priority=10,
            ),
            ParserRuleSpec(
                field=ParserField.SERIES_TITLE,
                pattern=r"(?P<series_title>.+)",
                priority=10,
            ),
        ),
    )

    assert "duplicate rule priority: 10" in validate_parser_profile(profile)


def test_parser_profile_validation_rejects_invalid_pattern() -> None:
    profile = ParserProfileSpec(
        release_group="ExampleSubs",
        version=1,
        rules=(
            ParserRuleSpec(
                field=ParserField.EPISODE_NUMBER,
                pattern="(",
            ),
        ),
    )

    errors = validate_parser_profile(profile)

    assert errors
    assert "missing" in errors[0] or "unterminated" in errors[0]


def test_parser_profile_validation_uses_multiple_samples() -> None:
    profile = ParserProfileSpec(
        release_group="ExampleSubs",
        version=3,
        rules=(
            ParserRuleSpec(
                field=ParserField.EPISODE_NUMBER,
                pattern=r"Episode-(?P<episode_number>\d{2})",
                priority=10,
                required=True,
                transform=ParserTransform.TO_INT,
            ),
        ),
    )

    results = validate_parser_samples(
        profile,
        (
            _release("[ExampleSubs] Anime Episode-01 [1080p].mkv"),
            _release("[ExampleSubs] Anime Episode-02 [1080p].mkv"),
        ),
        require_actionable=False,
    )

    assert [parsed.episode_number for _, parsed in results] == [1, 2]


def test_parser_profile_enforces_input_and_rule_limits() -> None:
    too_long = _release("x" * 1001)
    profile = ParserProfileSpec(
        release_group="ExampleSubs",
        version=1,
        rules=(
            ParserRuleSpec(
                field=ParserField.EPISODE_NUMBER,
                pattern=r"(?P<episode_number>\d+)",
            ),
        ),
    )

    with pytest.raises(ValueError, match="input"):
        parse_release(too_long, profile)

    with pytest.raises(ValueError, match="pattern"):
        parse_release(
            _release("Anime - 01"),
            profile=ParserProfileSpec(
                release_group="ExampleSubs",
                version=1,
                rules=(
                    ParserRuleSpec(
                        field=ParserField.EPISODE_NUMBER,
                        pattern="x" * 2001,
                    ),
                ),
            ),
        )
