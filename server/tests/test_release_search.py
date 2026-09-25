from dataclasses import replace

import pytest
from animedownloader_releases import (
    DEFAULT_SEARCH_TEMPLATES,
    Release,
    SearchProfileSpec,
    SearchQueryContext,
    SearchTemplateSpec,
    build_search_queries,
    merge_releases,
    normalize_release_group_slug,
    validate_search_profile,
    validate_search_template,
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




def test_normalize_release_group_slug() -> None:
    assert normalize_release_group_slug(" Example Subs ") == "example-subs"


def test_build_default_search_queries_progressively() -> None:
    context = SearchQueryContext(
        group="ExampleSubs",
        title="Frieren",
        episode=8,
        resolution="1080p",
        codec="HEVC",
    )

    assert build_search_queries(context) == (
        "ExampleSubs Frieren 8 1080p HEVC",
        "Frieren 8 1080p HEVC",
        "ExampleSubs Frieren 8",
        "Frieren 8",
        "ExampleSubs Frieren",
        "Frieren",
    )


def test_build_profile_search_queries_preserves_profile_order() -> None:
    profile = SearchProfileSpec(
        release_group="ExampleSubs",
        version=3,
        templates=(
            SearchTemplateSpec("{title} {episode} {codec}", priority=20),
            SearchTemplateSpec("{group} {title} {episode}", priority=10),
        ),
    )

    assert build_search_queries(
        SearchQueryContext(group="ExampleSubs", title="Frieren", episode=8, codec="HEVC"),
        profile,
    ) == (
        "ExampleSubs Frieren 8",
        "Frieren 8 HEVC",
    )


def test_build_search_queries_skips_templates_missing_all_values() -> None:
    profile = SearchProfileSpec(
        release_group="ExampleSubs",
        version=1,
        templates=(SearchTemplateSpec("{resolution} {codec}"),),
    )

    assert build_search_queries(
        SearchQueryContext(title="Frieren"),
        profile,
    ) == ()


def test_validate_search_template_rejects_unknown_placeholder() -> None:
    assert "unsupported search field: source" in validate_search_template("{title} {source}")


def test_validate_search_profile_rejects_duplicate_priorities() -> None:
    profile = SearchProfileSpec(
        release_group="ExampleSubs",
        version=1,
        templates=(
            SearchTemplateSpec("{title}", priority=10),
            SearchTemplateSpec("{episode}", priority=10),
        ),
    )

    assert "duplicate template priority: 10" in validate_search_profile(profile)


def test_merge_releases_deduplicates_source_and_info_hash() -> None:
    first = _release("[ExampleSubs] Frieren - 01")
    duplicate_source = replace(first)
    duplicate_hash = replace(first, id=first.id + "?duplicate")
    unique = replace(first, id=first.id + "?unique", info_hash="fedcba")

    assert merge_releases(((first,), (duplicate_source, duplicate_hash, unique))) == (
        first,
        unique,
    )


def test_search_template_length_limit() -> None:
    with pytest.raises(ValueError, match="template"):
        build_search_queries(
            SearchQueryContext(title="Frieren"),
            SearchProfileSpec(
                release_group="ExampleSubs",
                version=1,
                templates=(SearchTemplateSpec("x" * 301),),
            ),
        )


def test_default_templates_are_declared() -> None:
    assert len(DEFAULT_SEARCH_TEMPLATES) == 6
