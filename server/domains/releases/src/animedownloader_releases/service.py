from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .entities import (
    ParserProfileStatus,
    ReleaseGroup,
    ReleaseParserHealth,
    ReleaseParserObservation,
    ReleaseParserProfile,
    ReleaseParserRule,
    ReleaseParserSample,
)
from .exceptions import (
    InvalidReleaseParserProfileError,
    ReleaseGroupNotFoundError,
    ReleaseParserObservationNotFoundError,
    ReleaseParserProfileActivationError,
    ReleaseParserProfileNotFoundError,
    ReleaseParserSampleNotFoundError,
)
from .models import (
    ParsedRelease,
    ParserField,
    ParserProfileSpec,
    ParserRuleSpec,
    ParserTransform,
    ParseStatus,
    Release,
)
from .parser import parse_release, validate_parser_profile


@dataclass(frozen=True, slots=True)
class ParserSampleResult:
    sample_id: UUID
    title: str
    parsed: ParsedRelease | None
    error: str | None


@dataclass(frozen=True, slots=True)
class ParserValidationResult:
    valid: bool
    sample_count: int
    minimum_samples: int
    errors: tuple[str, ...]
    results: tuple[ParserSampleResult, ...]


@dataclass(frozen=True, slots=True)
class ParserDifference:
    sample_id: UUID
    title: str
    fields: dict[str, tuple[object, object]]


@dataclass(frozen=True, slots=True)
class ParserComparisonResult:
    profile_id: UUID
    draft_version: int
    active_version: int | None
    differences: tuple[ParserDifference, ...]


@dataclass(frozen=True, slots=True)
class ParserHealthResult:
    profile_id: UUID
    total_count: int
    parsed_count: int
    ambiguous_count: int
    unparsed_count: int
    unsupported_count: int
    failure_rate: float
    drift_signal: bool
    drift_reason: str | None
    recent_failures: tuple[ReleaseParserObservation, ...]


class ReleaseProfileService:
    MIN_VALIDATION_SAMPLES = 2
    MAX_RECENT_FAILURES = 20
    DRIFT_MIN_TOTAL = 8
    DRIFT_FAILURE_RATE = 0.25
    DRIFT_RECENT_FAILURES = 3

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_groups(self) -> list[ReleaseGroup]:
        result = await self.session.scalars(
            select(ReleaseGroup)
            .where(ReleaseGroup.enabled.is_(True))
            .order_by(func.lower(ReleaseGroup.name), ReleaseGroup.slug),
        )
        return list(result.all())

    async def get_group(self, group_id: UUID) -> ReleaseGroup:
        group = await self.session.scalar(
            select(ReleaseGroup).where(ReleaseGroup.id == group_id),
        )
        if group is None:
            raise ReleaseGroupNotFoundError(group_id)
        return group

    async def list_profiles(self, group_id: UUID) -> list[ReleaseParserProfile]:
        await self.get_group(group_id)
        result = await self.session.scalars(
            select(ReleaseParserProfile)
            .where(ReleaseParserProfile.release_group_id == group_id)
            .options(
                selectinload(ReleaseParserProfile.rules),
                selectinload(ReleaseParserProfile.health),
                selectinload(ReleaseParserProfile.release_group),
            )
            .order_by(ReleaseParserProfile.version.desc()),
        )
        return list(result.all())

    async def get_profile(self, profile_id: UUID) -> ReleaseParserProfile:
        profile = await self.session.scalar(
            select(ReleaseParserProfile)
            .where(ReleaseParserProfile.id == profile_id)
            .options(
                selectinload(ReleaseParserProfile.rules),
                selectinload(ReleaseParserProfile.release_group),
                selectinload(ReleaseParserProfile.health),
            ),
        )
        if profile is None:
            raise ReleaseParserProfileNotFoundError(profile_id)
        return profile

    async def create_draft(self, group_id: UUID) -> ReleaseParserProfile:
        await self.session.rollback()
        async with self.session.begin():
            group = await self.session.scalar(
                select(ReleaseGroup)
                .where(ReleaseGroup.id == group_id)
                .with_for_update(),
            )
            if group is None:
                raise ReleaseGroupNotFoundError(group_id)

            latest = await self.session.scalar(
                select(ReleaseParserProfile)
                .where(ReleaseParserProfile.release_group_id == group_id)
                .options(selectinload(ReleaseParserProfile.rules))
                .order_by(ReleaseParserProfile.version.desc())
                .limit(1),
            )

            if latest is not None and latest.status == ParserProfileStatus.DRAFT.value:
                profile_id = latest.id
            else:
                version = latest.version + 1 if latest else 1
                profile = ReleaseParserProfile(
                    release_group_id=group_id,
                    version=version,
                    status=ParserProfileStatus.DRAFT.value,
                )
                if latest is not None:
                    profile.rules = [
                        ReleaseParserRule(
                            field=rule.field,
                            pattern=rule.pattern,
                            priority=rule.priority,
                            required=rule.required,
                            flags=rule.flags,
                            transform=rule.transform,
                        )
                        for rule in latest.rules
                    ]
                self.session.add(profile)
                await self.session.flush()
                profile_id = profile.id

        return await self.get_profile(profile_id)

    async def update_rules(
        self,
        profile_id: UUID,
        rules: tuple[ParserRuleSpec, ...],
    ) -> ReleaseParserProfile:
        profile = await self.get_profile(profile_id)
        if profile.status != ParserProfileStatus.DRAFT.value:
            raise InvalidReleaseParserProfileError("only draft profiles can be edited")

        spec = self._to_spec(profile, rules=rules)
        errors = validate_parser_profile(spec)
        if errors:
            raise InvalidReleaseParserProfileError("; ".join(errors))

        await self.session.rollback()
        async with self.session.begin():
            profile = await self.get_profile(profile_id)
            if profile.status != ParserProfileStatus.DRAFT.value:
                raise InvalidReleaseParserProfileError("only draft profiles can be edited")
            profile.rules.clear()
            profile.rules.extend(
                ReleaseParserRule(
                    field=rule.field.value,
                    pattern=rule.pattern,
                    priority=rule.priority,
                    required=rule.required,
                    flags=rule.flags,
                    transform=rule.transform.value,
                )
                for rule in rules
            )

        return await self.get_profile(profile_id)

    async def list_samples(self, group_id: UUID) -> list[ReleaseParserSample]:
        await self.get_group(group_id)
        result = await self.session.scalars(
            select(ReleaseParserSample)
            .where(ReleaseParserSample.release_group_id == group_id)
            .order_by(ReleaseParserSample.created_at, ReleaseParserSample.id),
        )
        return list(result.all())

    async def add_sample(
        self,
        group_id: UUID,
        *,
        title: str,
        source: str = "nyaa",
    ) -> ReleaseParserSample:
        normalized_title = title.strip()
        normalized_source = source.strip() or "nyaa"
        if not normalized_title:
            raise ValueError("sample title must not be empty")
        if len(normalized_title) > 500:
            raise ValueError("sample title is too long")
        if len(normalized_source) > 32:
            raise ValueError("sample source is too long")

        await self.session.rollback()
        async with self.session.begin():
            await self.get_group(group_id)
            existing = await self.session.scalar(
                select(ReleaseParserSample).where(
                    ReleaseParserSample.release_group_id == group_id,
                    ReleaseParserSample.source == normalized_source,
                    ReleaseParserSample.title == normalized_title,
                ),
            )
            if existing is None:
                sample = ReleaseParserSample(
                    release_group_id=group_id,
                    source=normalized_source,
                    title=normalized_title,
                )
                self.session.add(sample)
                await self.session.flush()
            else:
                sample = existing

        return sample

    async def delete_sample(self, sample_id: UUID) -> None:
        await self.session.rollback()
        async with self.session.begin():
            sample = await self.session.scalar(
                select(ReleaseParserSample).where(ReleaseParserSample.id == sample_id),
            )
            if sample is None:
                raise ReleaseParserSampleNotFoundError(sample_id)
            await self.session.delete(sample)

    async def validate_profile(self, profile_id: UUID) -> ParserValidationResult:
        profile = await self.get_profile(profile_id)
        samples = await self.list_samples(profile.release_group_id)
        errors = list(validate_parser_profile(self._to_spec(profile)))

        if len(samples) < self.MIN_VALIDATION_SAMPLES:
            errors.append(
                f"at least {self.MIN_VALIDATION_SAMPLES} representative samples are required",
            )

        results: list[ParserSampleResult] = []
        profile_spec = self._to_spec(profile)
        for sample in samples:
            release = self._sample_release(sample)
            try:
                parsed = parse_release(release, profile_spec)
            except ValueError as exc:
                results.append(
                    ParserSampleResult(
                        sample_id=sample.id,
                        title=sample.title,
                        parsed=None,
                        error=str(exc),
                    ),
                )
                errors.append(f"{sample.title}: {exc}")
                continue

            sample_error = (
                None
                if parsed.is_actionable
                else "sample did not produce an actionable episode"
            )
            if sample_error is not None:
                errors.append(f"sample is not actionable: {sample.title}")
            results.append(
                ParserSampleResult(
                    sample_id=sample.id,
                    title=sample.title,
                    parsed=parsed,
                    error=sample_error,
                ),
            )

        return ParserValidationResult(
            valid=not errors and bool(samples),
            sample_count=len(samples),
            minimum_samples=self.MIN_VALIDATION_SAMPLES,
            errors=tuple(dict.fromkeys(errors)),
            results=tuple(results),
        )

    async def compare_with_active(self, profile_id: UUID) -> ParserComparisonResult:
        profile = await self.get_profile(profile_id)
        active = await self.session.scalar(
            select(ReleaseParserProfile)
            .where(
                ReleaseParserProfile.release_group_id == profile.release_group_id,
                ReleaseParserProfile.status == ParserProfileStatus.ACTIVE.value,
            )
            .options(
                selectinload(ReleaseParserProfile.rules),
                selectinload(ReleaseParserProfile.release_group),
            ),
        )
        samples = await self.list_samples(profile.release_group_id)

        differences: list[ParserDifference] = []
        draft_spec = self._to_spec(profile)
        active_spec = self._to_spec(active) if active is not None else None
        if (
            active is not None
            and active_spec is not None
            and active.id != profile.id
        ):
            for sample in samples:
                release = self._sample_release(sample)
                draft_parsed = parse_release(release, draft_spec)
                active_parsed = parse_release(release, active_spec)
                field_changes: dict[str, tuple[object, object]] = {}
                for field in (
                    "release_group",
                    "series_title",
                    "episode_number",
                    "episode_title",
                    "season_number",
                    "resolution",
                    "source",
                    "video_codec",
                    "audio_codec",
                    "bit_depth",
                    "status",
                ):
                    before = getattr(active_parsed, field)
                    after = getattr(draft_parsed, field)
                    if before != after:
                        field_changes[field] = (before, after)
                if field_changes:
                    differences.append(
                        ParserDifference(
                            sample_id=sample.id,
                            title=sample.title,
                            fields=field_changes,
                        ),
                    )

        return ParserComparisonResult(
            profile_id=profile.id,
            draft_version=profile.version,
            active_version=active.version if active is not None else None,
            differences=tuple(differences),
        )

    async def activate(self, profile_id: UUID) -> ReleaseParserProfile:
        validation = await self.validate_profile(profile_id)
        if not validation.valid:
            raise ReleaseParserProfileActivationError(
                "profile validation failed: " + "; ".join(validation.errors),
            )

        await self.session.rollback()
        async with self.session.begin():
            profile = await self.session.scalar(
                select(ReleaseParserProfile)
                .where(ReleaseParserProfile.id == profile_id)
                .options(selectinload(ReleaseParserProfile.release_group))
                .with_for_update(),
            )
            if profile is None:
                raise ReleaseParserProfileNotFoundError(profile_id)
            if profile.status != ParserProfileStatus.DRAFT.value:
                raise ReleaseParserProfileActivationError(
                    "only draft profiles can be activated",
                )

            current = await self.session.scalar(
                select(ReleaseParserProfile)
                .where(
                    ReleaseParserProfile.release_group_id == profile.release_group_id,
                    ReleaseParserProfile.status == ParserProfileStatus.ACTIVE.value,
                )
                .with_for_update(),
            )
            if current is not None:
                current.status = ParserProfileStatus.RETIRED.value
            profile.status = ParserProfileStatus.ACTIVE.value
            profile.activated_at = datetime.now(UTC)
            await self.session.flush()

        return await self.get_profile(profile_id)

    async def health(self, profile_id: UUID) -> ParserHealthResult:
        profile = await self.get_profile(profile_id)
        health = profile.health
        result = await self.session.scalars(
            select(ReleaseParserObservation)
            .where(ReleaseParserObservation.profile_id == profile_id)
            .order_by(
                ReleaseParserObservation.observed_at.desc(),
                ReleaseParserObservation.id.desc(),
            )
            .limit(self.MAX_RECENT_FAILURES),
        )
        recent_failures = tuple(result.all())

        total = health.total_count if health is not None else 0
        parsed = health.parsed_count if health is not None else 0
        ambiguous = health.ambiguous_count if health is not None else 0
        unparsed = health.unparsed_count if health is not None else 0
        unsupported = health.unsupported_count if health is not None else 0

        failure_count = total - parsed
        failure_rate = failure_count / total if total else 0.0
        recent_cutoff = datetime.now(UTC) - timedelta(hours=24)
        recent_count = sum(
            1 for item in recent_failures if item.observed_at >= recent_cutoff
        )

        drift_signal = (
            (total >= self.DRIFT_MIN_TOTAL and failure_rate >= self.DRIFT_FAILURE_RATE)
            or recent_count >= self.DRIFT_RECENT_FAILURES
        )
        if recent_count >= self.DRIFT_RECENT_FAILURES:
            drift_reason = (
                f"{recent_count} parser failures observed in the last 24 hours"
            )
        elif total >= self.DRIFT_MIN_TOTAL and failure_rate >= self.DRIFT_FAILURE_RATE:
            drift_reason = (
                f"parser failure rate is {failure_rate:.0%} across {total} observations"
            )
        else:
            drift_reason = None

        return ParserHealthResult(
            profile_id=profile_id,
            total_count=total,
            parsed_count=parsed,
            ambiguous_count=ambiguous,
            unparsed_count=unparsed,
            unsupported_count=unsupported,
            failure_rate=failure_rate,
            drift_signal=drift_signal,
            drift_reason=drift_reason,
            recent_failures=recent_failures,
        )

    async def record_parse_results(
        self,
        results: dict[UUID, tuple[UUID, tuple[tuple[Release, ParsedRelease], ...]]],
    ) -> None:
        if not results:
            return

        await self.session.rollback()
        async with self.session.begin():
            for profile_id, (group_id, observations) in results.items():
                if not observations:
                    continue

                health = await self.session.scalar(
                    select(ReleaseParserHealth)
                    .where(ReleaseParserHealth.profile_id == profile_id)
                    .with_for_update(),
                )
                if health is None:
                    health = ReleaseParserHealth(profile_id=profile_id)
                    self.session.add(health)

                for release, parsed in observations:
                    health.total_count += 1
                    if parsed.status == ParseStatus.PARSED:
                        health.parsed_count += 1
                        continue

                    if parsed.status == ParseStatus.AMBIGUOUS:
                        health.ambiguous_count += 1
                    elif parsed.status == ParseStatus.UNPARSED:
                        health.unparsed_count += 1
                    elif parsed.status == ParseStatus.UNSUPPORTED:
                        health.unsupported_count += 1

                    self.session.add(
                        ReleaseParserObservation(
                            release_group_id=group_id,
                            profile_id=profile_id,
                            source=release.source,
                            title=release.title,
                            status=parsed.status.value,
                            failed_required_fields=[
                                field.value for field in parsed.failed_required_fields
                            ],
                        ),
                    )

    async def create_draft_from_observation(
        self,
        observation_id: UUID,
    ) -> ReleaseParserProfile:
        observation = await self.session.scalar(
            select(ReleaseParserObservation).where(
                ReleaseParserObservation.id == observation_id,
            ),
        )
        if observation is None:
            raise ReleaseParserObservationNotFoundError(observation_id)

        profiles = await self.list_profiles(observation.release_group_id)
        draft = next(
            (
                item
                for item in profiles
                if item.status == ParserProfileStatus.DRAFT.value
            ),
            None,
        )

        await self.session.rollback()
        if draft is None:
            draft = await self.create_draft(observation.release_group_id)

        await self.add_sample(
            observation.release_group_id,
            title=observation.title,
            source=observation.source,
        )
        return await self.get_profile(draft.id)

    @staticmethod
    def _sample_release(sample: ReleaseParserSample) -> Release:
        return Release(
            source=sample.source,
            id=f"sample:{sample.id}",
            title=sample.title,
            page_url="https://example.invalid/sample",
            torrent_url="https://example.invalid/sample.torrent",
            published_at=None,
            size=None,
            seeders=None,
            leechers=None,
            downloads=None,
            info_hash=None,
        )

    @staticmethod
    def _to_spec(
        profile: ReleaseParserProfile,
        *,
        rules: tuple[ParserRuleSpec, ...] | None = None,
    ) -> ParserProfileSpec:
        return ParserProfileSpec(
            release_group=profile.release_group.name,
            version=profile.version,
            rules=rules
            if rules is not None
            else tuple(
                ParserRuleSpec(
                    field=ParserField(rule.field),
                    pattern=rule.pattern,
                    priority=rule.priority,
                    required=rule.required,
                    flags=rule.flags,
                    transform=ParserTransform(rule.transform),
                )
                for rule in profile.rules
            ),
        )
