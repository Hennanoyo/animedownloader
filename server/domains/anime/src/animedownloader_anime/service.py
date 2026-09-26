from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .commands import (
    AnimeCreateData,
    AnimeReleasePreferenceData,
    AnimeUpdateData,
    EpisodeCreateData,
    EpisodeUpdateData,
)
from .exceptions import AnimeNotFoundError, DuplicateEpisodeError, EpisodeNotFoundError
from .models import Anime, AnimeReleasePreference, Episode
from .repository import AnimeRepository, EpisodeRepository


class AnimeService:
    MAX_TITLE_LENGTH = 200
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.animes = AnimeRepository(session)
        self.episodes = EpisodeRepository(session)

    async def list_animes(self) -> list[Anime]:
        return await self.animes.list()

    async def get_anime(self, anime_id: UUID) -> Anime:
        anime = await self.animes.get(anime_id)
        if anime is None:
            raise AnimeNotFoundError(anime_id)
        return anime

    async def create_anime(self, data: AnimeCreateData) -> Anime:
        numbers = [episode.episode_number for episode in data.episodes]
        duplicates = {number for number in numbers if numbers.count(number) > 1}
        if duplicates:
            raise DuplicateEpisodeError(min(duplicates))

        async with self.session.begin():
            anime = Anime(
                title=data.title.strip(),
                titles=self._clean_titles(data.titles),
                year=data.year,
                season=data.season.value,
                weekday=data.weekday.value,
                air_time=data.air_time,
                timezone=data.timezone.strip(),
            )
            anime.episodes = [
                self._build_episode(anime, episode_data) for episode_data in data.episodes
            ]
            await self.animes.add(anime)

        await self.session.refresh(anime)
        return anime

    async def update_anime(self, anime_id: UUID, data: AnimeUpdateData) -> Anime:
        async with self.session.begin():
            anime = await self.get_anime(anime_id)
            if data.title is not None:
                anime.title = data.title.strip()
            if data.titles is not None:
                anime.titles = self._clean_titles(data.titles)
            if data.year is not None:
                anime.year = data.year
            if data.season is not None:
                anime.season = data.season.value
            if data.weekday is not None:
                anime.weekday = data.weekday.value
            if data.air_time is not None:
                anime.air_time = data.air_time
            if data.timezone is not None:
                anime.timezone = data.timezone.strip()

        await self.session.refresh(anime)
        return anime

    async def get_release_preference(
        self,
        anime_id: UUID,
    ) -> AnimeReleasePreference | None:
        anime = await self.get_anime(anime_id)
        return anime.release_preference

    async def update_release_preference(
        self,
        anime_id: UUID,
        data: AnimeReleasePreferenceData,
    ) -> AnimeReleasePreference:
        self._validate_release_preference(data)

        async with self.session.begin():
            anime = await self.get_anime(anime_id)
            preference = anime.release_preference
            if preference is None:
                preference = AnimeReleasePreference(anime_id=anime.id)
                anime.release_preference = preference
                self.session.add(preference)

            preference.release_group_id = data.release_group_id
            preference.resolution = data.resolution
            preference.video_codec = data.video_codec
            preference.source = data.source

        await self.session.refresh(preference)
        return preference

    @staticmethod
    def _validate_release_preference(
        data: AnimeReleasePreferenceData,
    ) -> None:
        limits = (
            ("resolution", data.resolution, 32),
            ("video codec", data.video_codec, 32),
            ("source", data.source, 32),
        )
        for label, value, limit in limits:
            if value is not None and len(value.strip()) > limit:
                raise ValueError(f"{label} is too long")

    async def delete_anime(self, anime_id: UUID) -> None:
        async with self.session.begin():
            anime = await self.get_anime(anime_id)
            await self.animes.delete(anime)

    async def list_episodes(self, anime_id: UUID) -> list[Episode]:
        await self.get_anime(anime_id)
        return await self.episodes.list_for_anime(anime_id)

    async def get_episode(self, episode_id: UUID) -> Episode:
        episode = await self.episodes.get(episode_id)
        if episode is None:
            raise EpisodeNotFoundError(episode_id)
        return episode

    async def create_episode(
        self,
        anime_id: UUID,
        data: EpisodeCreateData,
    ) -> Episode:
        async with self.session.begin():
            anime = await self.animes.get(anime_id)
            if anime is None:
                raise AnimeNotFoundError(anime_id)

            if await self.episodes.exists_number(anime_id, data.episode_number):
                raise DuplicateEpisodeError(data.episode_number)

            episode = self._build_episode(anime, data)
            await self.episodes.add(episode)

        await self.session.refresh(episode)
        return episode

    async def update_episode(self, episode_id: UUID, data: EpisodeUpdateData) -> Episode:
        async with self.session.begin():
            episode = await self.get_episode(episode_id)
            if data.episode_number is not None and await self.episodes.exists_number(
                episode.anime_id,
                data.episode_number,
                exclude_episode_id=episode_id,
            ):
                raise DuplicateEpisodeError(data.episode_number)

            if data.release_group_id is not None:
                episode.release_group_id = data.release_group_id
            if data.episode_number is not None:
                episode.episode_number = data.episode_number
            if data.title is not None:
                episode.title = data.title.strip()
            if data.source is not None:
                episode.source = data.source
            if data.source_id is not None:
                episode.source_id = data.source_id
            if data.source_title is not None:
                episode.source_title = data.source_title
            if data.source_url is not None:
                episode.source_url = data.source_url
            if data.torrent_url is not None:
                episode.torrent_url = data.torrent_url
            if data.size is not None:
                episode.size = data.size
            if data.seeders is not None:
                episode.seeders = data.seeders
            if data.leechers is not None:
                episode.leechers = data.leechers
            if data.downloads is not None:
                episode.downloads = data.downloads
            if data.info_hash is not None:
                episode.info_hash = data.info_hash
            if data.download_status is not None:
                episode.download_status = data.download_status.value
            if data.conversion_status is not None:
                episode.conversion_status = data.conversion_status.value

        await self.session.refresh(episode)
        return episode

    async def delete_episode(self, episode_id: UUID) -> None:
        async with self.session.begin():
            episode = await self.get_episode(episode_id)
            await self.episodes.delete(episode)

    @staticmethod
    def _clean_titles(titles: dict[str, str]) -> dict[str, str]:
        cleaned: dict[str, str] = {}
        for key, value in titles.items():
            normalized_key = key.strip().lower()
            normalized_value = value.strip()
            if not normalized_value:
                continue
            if len(normalized_value) > AnimeService.MAX_TITLE_LENGTH:
                raise ValueError(
                    f"anime title exceeds {AnimeService.MAX_TITLE_LENGTH} characters: "
                    f"{normalized_key}"
                )
            cleaned[normalized_key] = normalized_value
        return cleaned

    @staticmethod
    def _build_episode(anime: Anime, data: EpisodeCreateData) -> Episode:
        return Episode(
            anime=anime,
            release_group_id=data.release_group_id,
            episode_number=data.episode_number,
            title=data.title.strip(),
            source=data.source,
            source_id=data.source_id,
            source_title=data.source_title,
            source_url=data.source_url,
            torrent_url=data.torrent_url,
            size=data.size,
            seeders=data.seeders,
            leechers=data.leechers,
            downloads=data.downloads,
            info_hash=data.info_hash,
            download_status=data.download_status.value,
            conversion_status=data.conversion_status.value,
        )
