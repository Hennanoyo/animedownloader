from dataclasses import replace

from animedownloader_releases import (
    DEFAULT_SEARCH_FIELDS,
    Release,
    SearchField,
    SearchProfileSpec,
    SearchQueryContext,
    build_search_plan,
    build_search_query,
    merge_releases,
    normalize_release_group_slug,
    validate_search_profile,
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


def test_build_default_search_query() -> None:
    context = SearchQueryContext(
        group="ExampleSubs",
        title="Frieren",
        episode=8,
        resolution="1080p",
        codec="HEVC",
    )

    assert build_search_query(context) == "ExampleSubs Frieren 8 1080p HEVC"


def test_build_search_query_respects_field_order_and_selection() -> None:
    context = SearchQueryContext(
        group="ExampleSubs",
        title="Frieren",
        episode=8,
        resolution="1080p",
        codec="HEVC",
    )

    assert build_search_query(
        context,
        fields=(
            SearchField.TITLE,
            SearchField.GROUP,
            SearchField.EPISODE,
        ),
    ) == "Frieren ExampleSubs 8"


def test_build_search_query_skips_empty_selected_fields() -> None:
    context = SearchQueryContext(title="Frieren")

    assert build_search_query(
        context,
        fields=(SearchField.GROUP, SearchField.TITLE, SearchField.CODEC),
    ) == "Frieren"


def test_build_search_query_supports_source_field() -> None:
    context = SearchQueryContext(title="Frieren", source="WEB-DL")

    assert build_search_query(
        context,
        fields=(SearchField.TITLE, SearchField.SOURCE),
    ) == "Frieren WEB-DL"


def test_validate_search_profile_rejects_duplicate_fields() -> None:
    profile = SearchProfileSpec(
        release_group="ExampleSubs",
        version=1,
        fields=(SearchField.TITLE, SearchField.TITLE),
    )

    assert validate_search_profile(profile) == ("duplicate search field",)


def test_search_profile_uses_declared_field_order() -> None:
    profile = SearchProfileSpec(
        release_group="ExampleSubs",
        version=3,
        fields=(SearchField.TITLE, SearchField.EPISODE, SearchField.CODEC),
    )

    assert build_search_query(
        SearchQueryContext(title="Frieren", episode=8, codec="HEVC"),
        profile,
    ) == "Frieren 8 HEVC"


def test_build_search_plan_deduplicates_rendered_queries_and_preserves_order() -> None:
    contexts = (
        SearchQueryContext(title="Frieren", group="ExampleSubs"),
        SearchQueryContext(title="Frieren", group="ExampleSubs"),
        SearchQueryContext(title="Sousou no Frieren", group="ExampleSubs"),
    )

    plan = build_search_plan(
        contexts,
        fields=(SearchField.GROUP, SearchField.TITLE),
        max_queries=3,
    )

    assert tuple(item.query for item in plan.queries) == (
        "ExampleSubs Frieren",
        "ExampleSubs Sousou no Frieren",
    )


def test_build_search_plan_respects_query_budget() -> None:
    contexts = tuple(
        SearchQueryContext(title=title)
        for title in ("Frieren", "Sousou no Frieren", "Frieren: Beyond Journey's End")
    )

    plan = build_search_plan(
        contexts,
        fields=(SearchField.TITLE,),
        max_queries=2,
    )

    assert tuple(item.query for item in plan.queries) == (
        "Frieren",
        "Sousou no Frieren",
    )


def test_build_search_plan_uses_profile_fields() -> None:
    profile = SearchProfileSpec(
        release_group="ExampleSubs",
        version=2,
        fields=(SearchField.GROUP, SearchField.TITLE, SearchField.CODEC),
    )

    plan = build_search_plan(
        (
            SearchQueryContext(
                group="ExampleSubs",
                title="Frieren",
                codec="HEVC",
            ),
        ),
        profile=profile,
    )

    assert len(plan.queries) == 1
    assert plan.queries[0].query == "ExampleSubs Frieren HEVC"
    assert plan.queries[0].fields == profile.fields


def test_merge_releases_deduplicates_source_and_info_hash() -> None:
    first = _release("[ExampleSubs] Frieren - 01")
    duplicate_source = replace(first)
    duplicate_hash = replace(first, id=first.id + "?duplicate")
    unique = replace(first, id=first.id + "?unique", info_hash="fedcba")

    assert merge_releases(((first,), (duplicate_source, duplicate_hash, unique))) == (
        first,
        unique,
    )


def test_default_search_fields_are_declared() -> None:
    assert DEFAULT_SEARCH_FIELDS == (
        SearchField.GROUP,
        SearchField.TITLE,
        SearchField.EPISODE,
        SearchField.RESOLUTION,
        SearchField.CODEC,
    )