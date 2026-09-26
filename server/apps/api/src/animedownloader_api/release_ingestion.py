from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from animedownloader_anime import Anime, AnimeNotFoundError, Episode, EpisodeNotFoundError
from animedownloader_download import DownloadJob
from animedownloader_media_asset import MediaAsset
from animedownloader_media_processing import MediaProcessingJob
from animedownloader_releases import (
    EpisodeIngestionStatus,
    ParsedRelease,
    Release,
    ReleaseGroup,
    normalize_release_group_slug,
)
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from .release_matching import AnimeMatcher


class ReleaseNotActionableError(ValueError):
    pass


class ReleaseDoesNotMatchAnimeError(ValueError):
    pass


class ReleaseReplacementConflictError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EpisodeIngestionResult:
    status: EpisodeIngestionStatus
    episode: Episode | None
    existing_episode: Episode | None


class EpisodeIngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ingest(
        self,
        *,
        anime_id: UUID,
        release: Release,
        parsed: ParsedRelease,
    ) -> EpisodeIngestionResult:
        if not parsed.is_actionable:
            raise ReleaseNotActionableError(
                "release must have parsed status=parsed, a series title, and an episode number",
            )

        async with self.session.begin():
            anime = await self.session.scalar(
                select(Anime)
                .where(Anime.id == anime_id)
                .with_for_update(),
            )
            if anime is None:
                raise AnimeNotFoundError(anime_id)

            match = AnimeMatcher([anime]).match(parsed)
            if match.status.value != "matched" or not any(
                candidate.anime_id == anime.id for candidate in match.candidates
            ):
                raise ReleaseDoesNotMatchAnimeError(
                    "release series title does not match the selected anime",
                )

            identity_clauses: list[ColumnElement[bool]] = []
            if release.id:
                identity_clauses.append(Episode.source_id == release.id)
            if release.info_hash:
                identity_clauses.append(Episode.info_hash == release.info_hash)

            existing_by_identity = None
            if identity_clauses:
                existing_by_identity = await self.session.scalar(
                    select(Episode)
                    .where(
                        Episode.anime_id == anime.id,
                        Episode.source == release.source,
                        or_(*identity_clauses),
                    )
                    .with_for_update()
                    .limit(1),
                )

            release_group_id = await self._resolve_release_group_id(
                parsed.release_group,
            )

            if existing_by_identity is not None:
                self._update_release_metadata(
                    existing_by_identity,
                    release,
                    release_group_id=release_group_id,
                )
                return EpisodeIngestionResult(
                    status=EpisodeIngestionStatus.IDEMPOTENT,
                    episode=existing_by_identity,
                    existing_episode=None,
                )

            existing_episode = await self.session.scalar(
                select(Episode)
                .where(
                    Episode.anime_id == anime.id,
                    Episode.episode_number == parsed.episode_number,
                )
                .with_for_update()
            )
            if existing_episode is not None:
                return EpisodeIngestionResult(
                    status=EpisodeIngestionStatus.REPLACEMENT_CANDIDATE,
                    episode=None,
                    existing_episode=existing_episode,
                )

            episode = Episode(
                anime_id=anime.id,
                release_group_id=release_group_id,
                episode_number=parsed.episode_number,
                title=parsed.episode_title or f"Episode {parsed.episode_number}",
                source=release.source,
                source_id=release.id,
                source_title=release.title,
                source_url=release.page_url,
                torrent_url=release.torrent_url,
                size=release.size,
                seeders=release.seeders,
                leechers=release.leechers,
                downloads=release.downloads,
                info_hash=release.info_hash,
                download_status="not_started",
                conversion_status="not_started",
            )
            self.session.add(episode)
            await self.session.flush()

        await self.session.refresh(episode)
        return EpisodeIngestionResult(
            status=EpisodeIngestionStatus.CREATED,
            episode=episode,
            existing_episode=None,
        )

    async def replace(
        self,
        *,
        episode_id: UUID,
        release: Release,
        parsed: ParsedRelease,
    ) -> EpisodeIngestionResult:
        if not parsed.is_actionable:
            raise ReleaseNotActionableError(
                "release must have parsed status=parsed, a series title, and an episode number",
            )

        async with self.session.begin():
            episode = await self.session.scalar(
                select(Episode).where(Episode.id == episode_id).with_for_update(),
            )
            if episode is None:
                raise EpisodeNotFoundError(episode_id)

            anime = await self.session.scalar(
                select(Anime).where(Anime.id == episode.anime_id).with_for_update(),
            )
            if anime is None:
                raise AnimeNotFoundError(episode.anime_id)

            match = AnimeMatcher([anime]).match(parsed)
            if match.status.value != "matched" or not any(
                candidate.anime_id == anime.id for candidate in match.candidates
            ):
                raise ReleaseDoesNotMatchAnimeError(
                    "release series title does not match the selected anime",
                )

            if parsed.episode_number != episode.episode_number:
                raise ReleaseReplacementConflictError(
                    "release episode number does not match the existing Episode",
                )

            download_job_id = await self.session.scalar(
                select(DownloadJob.id)
                .where(DownloadJob.episode_id == episode_id)
                .limit(1),
            )
            if download_job_id is not None:
                raise ReleaseReplacementConflictError(
                    "release cannot be replaced after a DownloadJob has been created",
                )

            processing_job_id = await self.session.scalar(
                select(MediaProcessingJob.id)
                .where(MediaProcessingJob.episode_id == episode_id)
                .limit(1),
            )
            if processing_job_id is not None:
                raise ReleaseReplacementConflictError(
                    "release cannot be replaced after media processing history exists",
                )

            media_asset_id = await self.session.scalar(
                select(MediaAsset.id)
                .where(MediaAsset.episode_id == episode_id)
                .limit(1),
            )
            if media_asset_id is not None:
                raise ReleaseReplacementConflictError(
                    "release cannot be replaced after media assets exist",
                )

            release_group_id = await self._resolve_release_group_id(
                parsed.release_group,
            )
            self._update_release_metadata(
                episode,
                release,
                release_group_id=release_group_id,
            )

        await self.session.refresh(episode)
        return EpisodeIngestionResult(
            status=EpisodeIngestionStatus.REPLACED,
            episode=episode,
            existing_episode=None,
        )

    async def _resolve_release_group_id(
        self,
        release_group: str | None,
    ) -> UUID | None:
        if not release_group:
            return None

        normalized_slug = normalize_release_group_slug(release_group)
        return await self.session.scalar(
            select(ReleaseGroup.id)
            .where(
                ReleaseGroup.enabled.is_(True),
                or_(
                    ReleaseGroup.slug == normalized_slug,
                    func.lower(ReleaseGroup.name) == release_group.casefold(),
                ),
            )
            .limit(1),
        )

    @staticmethod
    def _update_release_metadata(
        episode: Episode,
        release: Release,
        *,
        release_group_id: UUID | None,
    ) -> None:
        if release_group_id is not None:
            episode.release_group_id = release_group_id
        episode.source = release.source
        episode.source_id = release.id
        episode.source_title = release.title
        episode.source_url = release.page_url
        episode.torrent_url = release.torrent_url
        episode.size = release.size
        episode.seeders = release.seeders
        episode.leechers = release.leechers
        episode.downloads = release.downloads
        episode.info_hash = release.info_hash
