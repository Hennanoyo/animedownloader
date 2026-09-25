from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from pathlib import PurePosixPath
from typing import Final

from .models import (
    SUPPORTED_PARSER_TRANSFORMS,
    ParseStatus,
    ParsedRelease,
    ParserField,
    ParserProfileSpec,
    ParserRuleSpec,
    ParserTransform,
    Release,
)

MAX_INPUT_LENGTH: Final = 1000
MAX_PATTERN_LENGTH: Final = 2000
MAX_RULES_PER_PROFILE: Final = 64
REGEX_TIMEOUT_SECONDS: Final = 0.05

_RESOLUTION_RE = re.compile(r"(?<!\w)(?P<value>2160p|1440p|1080p|720p|576p|480p|360p)(?!\w)", re.I)
_DIMENSIONS_RE = re.compile(r"(?<!\w)(?P<width>\d{3,4})x(?P<height>\d{3,4})(?!\w)", re.I)
_SOURCE_RE = re.compile(
    r"(?<!\w)(?P<value>web[- .]?dl|webrip|web|bluray|blu[- .]?ray|bdmv|hdtv)(?!\w)",
    re.I,
)
_VIDEO_CODEC_RE = re.compile(
    r"(?<!\w)(?P<value>hevc|h\.?265|x265|av1|avc|h\.?264|x264|vp9)(?!\w)",
    re.I,
)
_AUDIO_CODEC_RE = re.compile(
    r"(?<!\w)(?P<value)e[- .]?ac[- .]?3|eac3|ac3|aac|flac|opus|vorbis|dts(?:[- .]?hd)?(?:[- .]?ma)?",
    re.I,
)
_BIT_DEPTH_RE = re.compile(r"(?<!\w)(?P<value>8|10|12)[- ]?bit(?!\w)", re.I)
_SEASON_EPISODE_RE = re.compile(
    r"(?<!\w)S(?P<season>\d{1,2})[ ._-]*E(?P<episode>\d{1,4})(?!\w)",
    re.I,
)
_EPISODE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<episode>\d{1,4})(?![A-Za-z0-9])",
)
_LEADING_GROUP_RE = re.compile(r"^\[(?P<group>[^\]]{1,128})\]\s*")
_TECHNICAL_BRACKET_RE = re.compile(r"\[[^\]]+\]|\([^\)]+\)")


def normalize_release_title(title: str) -> str:
    value = unicodedata.normalize("NFKC", title).strip()
    value = _remove_extension(value)
    value = re.sub(r"\s+", " ", value)
    return value


def parse_release(
    release: Release,
    profile: ParserProfileSpec | None = None,
) -> ParsedRelease:
    normalized = normalize_release_title(release.title)
    if len(normalized) > MAX_INPUT_LENGTH:
        raise ValueError(f"release title exceeds {MAX_INPUT_LENGTH} characters")
    if not normalized:
        return ParsedRelease(
            source=release.source,
            source_id=release.id,
            original_title=release.title,
            normalized_title=normalized,
            release_group=None,
            series_title=None,
            episode_number=None,
            episode_title=None,
            season_number=None,
            resolution=None,
            source=None,
            video_codec=None,
            audio_codec=None,
            bit_depth=None,
            status=ParseStatus.UNPARSED,
            warnings=("release title is empty",),
        )

    generic = _parse_generic(release, normalized)
    if profile is None:
        return generic

    return apply_parser_profile(generic, profile)


def apply_parser_profile(
    parsed: ParsedRelease,
    profile: ParserProfileSpec,
) -> ParsedRelease:
    if not profile.rules:
        return replace(parsed, parser_profile_version=profile.version)

    if len(profile.rules) > MAX_RULES_PER_PROFILE:
        raise ValueError(f"parser profile exceeds {MAX_RULES_PER_PROFILE} rules")

    values: dict[ParserField, str | int | None] = {
        ParserField.RELEASE_GROUP: parsed.release_group,
        ParserField.SERIES_TITLE: parsed.series_title,
        ParserField.EPISODE_NUMBER: parsed.episode_number,
        ParserField.EPISODE_TITLE: parsed.episode_title,
        ParserField.SEASON_NUMBER: parsed.season_number,
        ParserField.RESOLUTION: parsed.resolution,
        ParserField.SOURCE: parsed.source,
        ParserField.VIDEO_CODEC: parsed.video_codec,
        ParserField.AUDIO_CODEC: parsed.audio_codec,
        ParserField.BIT_DEPTH: parsed.bit_depth,
    }
    warnings = list(parsed.warnings)
    failed_required: list[ParserField] = list(parsed.failed_required_fields)

    for rule in sorted(profile.rules, key=lambda item: item.priority):
        _validate_rule(rule)
        pattern = re.compile(rule.pattern, _parse_flags(rule.flags))
        match = pattern.search(parsed.normalized_title)
        if match is None:
            if rule.required and rule.field not in failed_required:
                failed_required.append(rule.field)
            continue

        value = match.groupdict().get(rule.field.value)
        if value is None:
            value = match.group(0)
        try:
            values[rule.field] = _transform(value, rule.transform)
        except ValueError as exc:
            warnings.append(f"{rule.field.value}: {exc}")

    if failed_required:
        status = ParseStatus.UNPARSED
    elif not values[ParserField.SERIES_TITLE] or values[ParserField.EPISODE_NUMBER] is None:
        status = ParseStatus.AMBIGUOUS
    else:
        status = ParseStatus.PARSED

    episode_number = _as_int(values[ParserField.EPISODE_NUMBER])
    season_number = _as_int(values[ParserField.SEASON_NUMBER])
    bit_depth = _as_int(values[ParserField.BIT_DEPTH])

    return ParsedRelease(
        source=parsed.source,
        source_id=parsed.source_id,
        original_title=parsed.original_title,
        normalized_title=parsed.normalized_title,
        release_group=_as_str(values[ParserField.RELEASE_GROUP]),
        series_title=_as_str(values[ParserField.SERIES_TITLE]),
        episode_number=episode_number,
        episode_title=_as_str(values[ParserField.EPISODE_TITLE]),
        season_number=season_number,
        resolution=_as_str(values[ParserField.RESOLUTION]),
        source=_as_str(values[ParserField.SOURCE]),
        video_codec=_as_str(values[ParserField.VIDEO_CODEC]),
        audio_codec=_as_str(values[ParserField.AUDIO_CODEC]),
        bit_depth=bit_depth,
        status=status,
        warnings=tuple(dict.fromkeys(warnings)),
        failed_required_fields=tuple(failed_required),
        parser_profile_version=profile.version,
    )


def validate_parser_profile(profile: ParserProfileSpec) -> tuple[str, ...]:
    if profile.version < 1:
        raise ValueError("parser profile version must be >= 1")
    if not profile.release_group.strip():
        raise ValueError("release group must not be empty")
    if len(profile.rules) > MAX_RULES_PER_PROFILE:
        raise ValueError(f"parser profile exceeds {MAX_RULES_PER_PROFILE} rules")

    priorities: set[int] = set()
    errors: list[str] = []
    for rule in profile.rules:
        try:
            _validate_rule(rule)
            re.compile(rule.pattern, _parse_flags(rule.flags))
        except (TypeError, ValueError, re.error) as exc:
            errors.append(f"priority {rule.priority}: {exc}")
        if rule.priority in priorities:
            errors.append(f"duplicate rule priority: {rule.priority}")
        priorities.add(rule.priority)
    return tuple(errors)


def validate_parser_samples(
    profile: ParserProfileSpec,
    releases: tuple[Release, ...],
    *,
    require_actionable: bool = False,
) -> tuple[tuple[Release, ParsedRelease], ...]:
    errors = validate_parser_profile(profile)
    if errors:
        raise ValueError("; ".join(errors))
    if not releases:
        raise ValueError("at least one sample release is required")

    results: list[tuple[Release, ParsedRelease]] = []
    for release in releases:
        parsed = parse_release(release, profile)
        if require_actionable and not parsed.is_actionable:
            raise ValueError(
                f"sample could not be parsed as an actionable episode: {release.title}"
            )
        results.append((release, parsed))
    return tuple(results)


def _parse_generic(release: Release, normalized: str) -> ParsedRelease:
    group_match = _LEADING_GROUP_RE.match(normalized)
    release_group = group_match.group("group").strip() if group_match else None
    if release_group and _looks_like_technical_token(release_group):
        release_group = None

    working = normalized[group_match.end() :].strip() if group_match else normalized
    season_number: int | None = None
    episode_number: int | None = None

    season_match = _SEASON_EPISODE_RE.search(working)
    episode_start: int | None = None
    episode_end: int | None = None
    warnings: list[str] = []

    if season_match:
        season_number = int(season_match.group("season"))
        episode_number = int(season_match.group("episode"))
        episode_start = season_match.start()
        episode_end = season_match.end()
    else:
        numeric_candidates = [
            match
            for match in _EPISODE_RE.finditer(_strip_technical_regions(working))
            if _is_plausible_episode(match.group("episode"))
        ]
        if len(numeric_candidates) == 1:
            candidate = numeric_candidates[0]
            episode_number = int(candidate.group("episode"))
            episode_start = candidate.start()
            episode_end = candidate.end()
        elif len(numeric_candidates) > 1:
            warnings.append("multiple plausible episode numbers were found")

    if episode_number is None:
        status = (
            ParseStatus.AMBIGUOUS
            if warnings
            else ParseStatus.UNPARSED
        )
        return _build_result(
            release,
            normalized,
            release_group=release_group,
            series_title=_clean_series_title(working, None, None),
            episode_number=None,
            episode_title=None,
            season_number=season_number,
            status=status,
            resolution=_extract(_RESOLUTION_RE, normalized),
            source=_normalize_source(_extract(_SOURCE_RE, normalized)),
            video_codec=_normalize_codec(_extract(_VIDEO_CODEC_RE, normalized)),
            audio_codec=_normalize_codec(_extract(_AUDIO_CODEC_RE, normalized)),
            bit_depth=_as_int(_extract(_BIT_DEPTH_RE, normalized)),
            warnings=warnings,
        )

    episode_title = _extract_episode_title(working, episode_end)
    series_title = _clean_series_title(working, episode_start, episode_end)
    status = ParseStatus.PARSED if series_title else ParseStatus.AMBIGUOUS

    return _build_result(
        release,
        normalized,
        release_group=release_group,
        series_title=series_title,
        episode_number=episode_number,
        episode_title=episode_title,
        season_number=season_number,
        status=status,
        resolution=_extract(_RESOLUTION_RE, normalized),
        source=_normalize_source(_extract(_SOURCE_RE, normalized)),
        video_codec=_normalize_codec(_extract(_VIDEO_CODEC_RE, normalized)),
        audio_codec=_normalize_codec(_extract(_AUDIO_CODEC_RE, normalized)),
        bit_depth=_as_int(_extract(_BIT_DEPTH_RE, normalized)),
        warnings=warnings,
    )


def _build_result(
    release: Release,
    normalized: str,
    *,
    release_group: str | None,
    series_title: str | None,
    episode_number: int | None,
    episode_title: str | None,
    season_number: int | None,
    resolution: str | None,
    source: str | None,
    video_codec: str | None,
    audio_codec: str | None,
    bit_depth: int | None,
    status: ParseStatus,
    warnings: list[str] | tuple[str, ...],
    failed_required_fields: tuple[ParserField, ...] = (),
    parser_profile_version: int | None = None,
) -> ParsedRelease:
    return ParsedRelease(
        source=release.source,
        source_id=release.id,
        original_title=release.title,
        normalized_title=normalized,
        release_group=release_group,
        series_title=series_title,
        episode_number=episode_number,
        episode_title=episode_title,
        season_number=season_number,
        resolution=resolution,
        source=source,
        video_codec=video_codec,
        audio_codec=audio_codec,
        bit_depth=bit_depth,
        status=status,
        warnings=tuple(dict.fromkeys(warnings)),
        failed_required_fields=failed_required_fields,
        parser_profile_version=parser_profile_version,
    )


def _extract(pattern: re.Pattern[str], value: str) -> str | None:
    match = pattern.search(value)
    return match.group("value") if match else None


def _extract_episode_title(value: str, episode_end: int | None) -> str | None:
    if episode_end is None:
        return None

    tail = value[episode_end:]
    tail = _TECHNICAL_BRACKET_RE.sub(" ", tail)
    tail = re.sub(r"^[\s._-]+", "", tail)
    tail = re.sub(r"[\s._-]+$", "", tail)
    return tail.strip() or None


def _clean_series_title(value: str, episode_start: int | None, episode_end: int | None) -> str | None:
    if episode_start is None:
        candidate = _TECHNICAL_BRACKET_RE.sub(" ", value)
    else:
        candidate = value[:episode_start]
    candidate = re.sub(r"[\s._-]+$", "", candidate)
    candidate = re.sub(r"^[\s._-]+", "", candidate)
    candidate = _TECHNICAL_BRACKET_RE.sub(" ", candidate)
    candidate = re.sub(r"\s+", " ", candidate)
    return candidate.strip() or None


def _strip_technical_regions(value: str) -> str:
    return _TECHNICAL_BRACKET_RE.sub(" ", value)


def _is_plausible_episode(value: str) -> bool:
    number = int(value)
    return number > 0 and not 1800 <= number <= 2099 and number < 1000


def _looks_like_technical_token(value: str) -> bool:
    lowered = value.casefold()
    return any(token in lowered for token in ("1080", "720", "2160", "hevc", "x265", "web", "bluray"))


def _normalize_codec(value: str | None) -> str | None:
    if value is None:
        return None
    lowered = value.casefold()
    aliases = {
        "h.265": "HEVC",
        "h265": "HEVC",
        "x265": "HEVC",
        "hevc": "HEVC",
        "h.264": "AVC",
        "h264": "AVC",
        "x264": "AVC",
        "avc": "AVC",
        "av1": "AV1",
        "vp9": "VP9",
    }
    return aliases.get(lowered.replace("-", "").replace(" ", ""), value.upper())


def _normalize_source(value: str | None) -> str | None:
    if value is None:
        return None
    lowered = value.casefold().replace(" ", "-").replace(".", "-")
    if lowered.startswith("blu-ray"):
        return "BluRay"
    if lowered.startswith("bluray"):
        return "BluRay"
    if lowered == "web-dl":
        return "WEB-DL"
    return value.upper()


def _remove_extension(value: str) -> str:
    suffix = PurePosixPath(value).suffix.casefold()
    if suffix in {".mkv", ".mp4", ".webm", ".avi", ".mov", ".ts"}:
        return value[: -len(suffix)]
    return value


def _validate_rule(rule: ParserRuleSpec) -> None:
    if rule.priority < 0:
        raise ValueError("priority must be >= 0")
    if len(rule.pattern) > MAX_PATTERN_LENGTH:
        raise ValueError(f"pattern exceeds {MAX_PATTERN_LENGTH} characters")
    if rule.transform not in SUPPORTED_PARSER_TRANSFORMS:
        raise ValueError(f"unsupported transform: {rule.transform}")
    _parse_flags(rule.flags)


def _parse_flags(flags: str) -> re.RegexFlag:
    result = re.RegexFlag(0)
    allowed = {"a": re.ASCII, "i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL, "x": re.VERBOSE}
    for flag in flags:
        try:
            result |= allowed[flag]
        except KeyError as exc:
            raise ValueError(f"unsupported regex flag: {flag}") from exc
    return result


def _transform(value: str, transform: ParserTransform) -> str | int:
    if transform == ParserTransform.IDENTITY:
        return value
    if transform == ParserTransform.STRIP:
        return value.strip()
    if transform == ParserTransform.NORMALIZE_SPACES:
        return re.sub(r"\s+", " ", value).strip()
    if transform == ParserTransform.TO_INT:
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError("value is not an integer") from exc
    if transform == ParserTransform.LOWER:
        return value.lower()
    if transform == ParserTransform.UPPER:
        return value.upper()
    raise ValueError(f"unsupported transform: {transform}")


def _as_str(value: str | int | None) -> str | None:
    return value if isinstance(value, str) else None


def _as_int(value: str | int | None) -> int | None:
    if isinstance(value, int):
        return value
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
