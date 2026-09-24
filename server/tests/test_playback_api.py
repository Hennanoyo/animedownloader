from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest
from animedownloader_anime import AnimeService
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import get_playback_service
from animedownloader_api.playback import PlaybackService
from animedownloader_api.schemas import PlaybackResponse
from animedownloader_media_asset import (
    MediaAttachmentStatus,
    MediaThumbnailStatus,
    SubtitleTrackStatus,
)
from animedownloader_media_processing import MediaStreamingRepresentationStatus


class FakeStorage:
    async def put_file(
        self,
        source_path: Path,
        object_key: str,
        *,
        content_type: str | None = None,
    ) -> None:
        raise NotImplementedError

    async def materialize(self, object_key: str, destination: Path) -> Path:
        raise NotImplementedError

    async def exists(self, object_key: str) -> bool:
        raise NotImplementedError

    async def delete(self, object_key: str) -> None:
        raise NotImplementedError

    def public_url(self, object_key: str) -> str:
        return "https://media.example.test/" + object_key


@pytest.mark.anyio
async def test_playback_service_exposes_only_current_ready_resources() -> None:
    episode_id = uuid7()
    asset_id = uuid7()
    variant_id = uuid7()
    now = datetime(2026, 9, 24, tzinfo=UTC)

    episode = SimpleNamespace(
        id=episode_id,
        anime_id=uuid7(),
        episode_number=1,
        title="Episode 01",
    )
    asset = SimpleNamespace(
        id=asset_id,
        path="/data/media/episode.mkv",
        metadata_updated_at=now,
        duration_seconds=12.0,
        subtitle_tracks=[
            SimpleNamespace(
                id=uuid7(),
                language="ko",
                title="Korean",
                is_default=True,
                is_forced=False,
                normalized_format="ass",
                normalized_path="subtitles/asset/track.ass",
                processing_status=SubtitleTrackStatus.COMPLETED,
            ),
            SimpleNamespace(
                id=uuid7(),
                language="en",
                title="English",
                is_default=False,
                is_forced=False,
                normalized_format="ass",
                normalized_path=None,
                processing_status=SubtitleTrackStatus.FAILED,
            ),
        ],
        attachments=[
            SimpleNamespace(
                processing_status=MediaAttachmentStatus.COMPLETED,
                font=SimpleNamespace(
                    id=uuid7(),
                    name="NotoSans.ttf",
                    mime_type="font/ttf",
                    path="fonts/ab/abcdef.ttf",
                ),
            ),
            SimpleNamespace(
                processing_status=MediaAttachmentStatus.COMPLETED,
                font=SimpleNamespace(
                    id=uuid7(),
                    name="Other.ttf",
                    mime_type="font/ttf",
                    path="fonts/cd/other.ttf",
                ),
            ),
        ],
        chapters=[
            SimpleNamespace(
                id=uuid7(),
                title="Opening",
                start_time_seconds=0.0,
                end_time_seconds=1.0,
            ),
        ],
        thumbnail_processing_status=MediaThumbnailStatus.COMPLETED,
        thumbnail_sprite_path="thumbnails/asset/sprite.jpg",
        thumbnail_vtt_path="thumbnails/asset/sprite.vtt",
    )
    font_id = asset.attachments[0].font.id
    asset.attachments.append(
        SimpleNamespace(
            processing_status=MediaAttachmentStatus.COMPLETED,
            font=SimpleNamespace(
                id=font_id,
                name="NotoSans.ttf",
                mime_type="font/ttf",
                path="fonts/ab/abcdef.ttf",
            ),
        ),
    )

    variant = SimpleNamespace(
        id=variant_id,
        path="playable/asset/variant.mp4",
        updated_at=now,
    )
    variant.is_current = lambda **_: True

    package = SimpleNamespace(
        representations=[
            SimpleNamespace(
                representation_status=MediaStreamingRepresentationStatus.COMPLETED,
            ),
        ],
        hls_master_key="streaming/package/master.m3u8",
        dash_manifest_key="streaming/package/manifest.mpd",
    )
    package.is_current = lambda **_: True

    anime_service = MagicMock(spec=AnimeService)
    anime_service.get_episode = AsyncMock(return_value=episode)
    media_asset_service = MagicMock()
    media_asset_service.get_for_episode = AsyncMock(return_value=asset)
    media_variant_service = MagicMock()
    media_variant_service.get_playable_variant = AsyncMock(return_value=variant)
    streaming_package_service = MagicMock()
    streaming_package_service.get_for_variant = AsyncMock(return_value=package)

    service = PlaybackService(
        anime_service=anime_service,
        media_asset_service=media_asset_service,
        media_variant_service=media_variant_service,
        streaming_package_service=streaming_package_service,
        storage=FakeStorage(),
    )

    result = await service.get_episode_playback(episode_id)

    assert result.video is not None
    assert result.video.direct is not None
    assert result.video.direct.url.endswith("playable/asset/variant.mp4")
    assert result.video.hls is not None
    assert result.video.dash is not None
    assert len(result.subtitles) == 1
    assert result.subtitles[0].language == "ko"
    assert result.subtitles[0].url.endswith("subtitles/asset/track.ass")
    assert len(result.fonts) == 2
    assert len(result.chapters) == 1
    assert result.thumbnails is not None
    assert result.thumbnails.sprite_url.endswith("thumbnails/asset/sprite.jpg")
    assert result.thumbnails.vtt_url.endswith("thumbnails/asset/sprite.vtt")


@pytest.mark.anyio
async def test_playback_service_hides_stale_video_and_incomplete_streaming() -> None:
    episode_id = uuid7()
    asset_id = uuid7()
    variant_id = uuid7()
    now = datetime(2026, 9, 24, tzinfo=UTC)

    episode = SimpleNamespace(
        id=episode_id,
        anime_id=uuid7(),
        episode_number=2,
        title="Episode 02",
    )
    asset = SimpleNamespace(
        id=asset_id,
        path="/data/media/episode-02.mkv",
        metadata_updated_at=now,
        duration_seconds=24.0,
        subtitle_tracks=[],
        attachments=[],
        chapters=[],
        thumbnail_processing_status=MediaThumbnailStatus.PROCESSING,
        thumbnail_sprite_path=None,
        thumbnail_vtt_path=None,
    )
    variant = SimpleNamespace(
        id=variant_id,
        path="playable/asset/variant.mp4",
        updated_at=now,
    )
    variant.is_current = lambda **_: False

    anime_service = MagicMock(spec=AnimeService)
    anime_service.get_episode = AsyncMock(return_value=episode)
    media_asset_service = MagicMock()
    media_asset_service.get_for_episode = AsyncMock(return_value=asset)
    media_variant_service = MagicMock()
    media_variant_service.get_playable_variant = AsyncMock(return_value=variant)
    streaming_package_service = MagicMock()

    service = PlaybackService(
        anime_service=anime_service,
        media_asset_service=media_asset_service,
        media_variant_service=media_variant_service,
        streaming_package_service=streaming_package_service,
        storage=FakeStorage(),
    )

    result = await service.get_episode_playback(episode_id)

    assert result.video is None
    assert result.thumbnails is None
    streaming_package_service.get_for_variant.assert_not_awaited()


@pytest.mark.anyio
async def test_get_episode_playback_returns_contract() -> None:
    episode_id = uuid7()
    playback = PlaybackResponse(
        anime_id=uuid7(),
        episode_id=episode_id,
        episode_number=3,
        title="Episode 03",
        duration_seconds=36.0,
        video=None,
        subtitles=[],
        fonts=[],
        chapters=[],
        thumbnails=None,
    )
    service = MagicMock(spec=PlaybackService)
    service.get_episode_playback = AsyncMock(return_value=playback)

    app = create_app()
    app.dependency_overrides[get_playback_service] = lambda: service

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/api/episodes/{episode_id}/playback")

    assert response.status_code == 200
    assert PlaybackResponse.model_validate(response.json()) == playback
    service.get_episode_playback.assert_awaited_once_with(episode_id)
