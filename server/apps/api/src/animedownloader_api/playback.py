from uuid import UUID

from animedownloader_anime import AnimeService
from animedownloader_media_asset import (
    MediaAsset,
    MediaAssetService,
    MediaAttachment,
    MediaAttachmentStatus,
    MediaThumbnailStatus,
    SubtitleTrackStatus,
)
from animedownloader_media_processing import (
    MediaStreamingPackageService,
    MediaStreamingRepresentationStatus,
    MediaVariantService,
)
from animedownloader_storage import Storage

from .schemas import (
    PlaybackChapterResponse,
    PlaybackFontResponse,
    PlaybackResponse,
    PlaybackSourceResponse,
    PlaybackSubtitleResponse,
    PlaybackThumbnailResponse,
    PlaybackVideoResponse,
)


class PlaybackService:
    def __init__(
        self,
        *,
        anime_service: AnimeService,
        media_asset_service: MediaAssetService,
        media_variant_service: MediaVariantService,
        streaming_package_service: MediaStreamingPackageService,
        storage: Storage,
    ) -> None:
        self._anime_service = anime_service
        self._media_asset_service = media_asset_service
        self._media_variant_service = media_variant_service
        self._streaming_package_service = streaming_package_service
        self._storage = storage

    async def get_episode_playback(self, episode_id: UUID) -> PlaybackResponse:
        episode = await self._anime_service.get_episode(episode_id)
        asset = await self._media_asset_service.get_for_episode(episode_id)

        if asset is None or asset.metadata_updated_at is None:
            return _empty_playback(
                episode.id,
                episode.episode_number,
                episode.title,
            )

        variant = await self._media_variant_service.get_playable_variant(asset.id)
        video = None
        if (
            variant is not None
            and variant.path is not None
            and variant.is_current(
                source_path=asset.path,
                source_metadata_updated_at=asset.metadata_updated_at,
            )
        ):
            video = PlaybackVideoResponse(
                direct=PlaybackSourceResponse(
                    url=self._storage.public_url(variant.path),
                    mime_type="video/mp4",
                ),
                hls=None,
                dash=None,
            )

            package = await self._streaming_package_service.get_for_variant(variant.id)
            if (
                package is not None
                and package.is_current(
                    source_path=variant.path,
                    source_variant_updated_at=variant.updated_at,
                )
                and any(
                    representation.representation_status
                    is MediaStreamingRepresentationStatus.COMPLETED
                    for representation in package.representations
                )
                and package.hls_master_key is not None
                and package.dash_manifest_key is not None
            ):
                video = video.model_copy(
                    update={
                        "hls": PlaybackSourceResponse(
                            url=self._storage.public_url(package.hls_master_key),
                            mime_type="application/vnd.apple.mpegurl",
                        ),
                        "dash": PlaybackSourceResponse(
                            url=self._storage.public_url(package.dash_manifest_key),
                            mime_type="application/dash+xml",
                        ),
                    },
                )

        subtitles = [
            PlaybackSubtitleResponse(
                id=track.id,
                language=track.language,
                title=track.title,
                is_default=track.is_default,
                is_forced=track.is_forced,
                format=track.normalized_format,
                url=self._storage.public_url(track.normalized_path),
            )
            for track in asset.subtitle_tracks
            if track.processing_status is SubtitleTrackStatus.COMPLETED
            and track.normalized_path is not None
        ]

        return PlaybackResponse(
            episode_id=episode.id,
            episode_number=episode.episode_number,
            title=episode.title,
            duration_seconds=asset.duration_seconds,
            video=video,
            subtitles=subtitles,
            fonts=_build_fonts(asset.attachments, self._storage),
            chapters=[
                PlaybackChapterResponse(
                    id=chapter.id,
                    title=chapter.title,
                    start_time_seconds=chapter.start_time_seconds,
                    end_time_seconds=chapter.end_time_seconds,
                )
                for chapter in asset.chapters
            ],
            thumbnails=_build_thumbnails(asset, self._storage),
        )


def _empty_playback(
    episode_id: UUID,
    episode_number: int,
    title: str,
) -> PlaybackResponse:
    return PlaybackResponse(
        episode_id=episode_id,
        episode_number=episode_number,
        title=title,
        duration_seconds=None,
        video=None,
        subtitles=[],
        fonts=[],
        chapters=[],
        thumbnails=None,
    )


def _build_fonts(
    attachments: list[MediaAttachment],
    storage: Storage,
) -> list[PlaybackFontResponse]:
    result: list[PlaybackFontResponse] = []
    seen: set[UUID] = set()

    for attachment in attachments:
        if attachment.processing_status is not MediaAttachmentStatus.COMPLETED:
            continue
        font = attachment.font
        if font is None or font.id in seen:
            continue
        seen.add(font.id)
        result.append(
            PlaybackFontResponse(
                id=font.id,
                name=font.name,
                mime_type=font.mime_type,
                url=storage.public_url(font.path),
            ),
        )

    return result


def _build_thumbnails(
    asset: MediaAsset,
    storage: Storage,
) -> PlaybackThumbnailResponse | None:
    if (
        asset.thumbnail_processing_status is not MediaThumbnailStatus.COMPLETED
        or asset.thumbnail_sprite_path is None
        or asset.thumbnail_vtt_path is None
    ):
        return None

    return PlaybackThumbnailResponse(
        sprite_url=storage.public_url(asset.thumbnail_sprite_path),
        vtt_url=storage.public_url(asset.thumbnail_vtt_path),
    )
