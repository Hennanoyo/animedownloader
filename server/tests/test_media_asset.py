from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import pytest
from animedownloader_media import (
    MediaFormat,
    MediaProbe,
    MediaStream,
    MediaStreamType,
)
from animedownloader_media_asset import MediaAssetService, MediaAssetValidationError


def make_probe(
    path: Path,
    *,
    video: bool = True,
    audio: bool = True,
) -> MediaProbe:
    streams: list[MediaStream] = []
    if video:
        streams.append(
            MediaStream(
                index=0,
                codec_type=MediaStreamType.VIDEO,
                codec_name="hevc",
                codec_long_name=None,
                profile=None,
                codec_tag_string=None,
                width=1920,
                height=1080,
                pixel_format="yuv420p10le",
                frame_rate="24000/1001",
                duration_seconds=60.0,
                bit_rate=900,
                channels=None,
                channel_layout=None,
                sample_rate_hz=None,
                language=None,
                title=None,
                disposition_default=True,
                disposition_forced=False,
                tags=(),
            ),
        )
    if audio:
        streams.append(
            MediaStream(
                index=1,
                codec_type=MediaStreamType.AUDIO,
                codec_name="aac",
                codec_long_name=None,
                profile=None,
                codec_tag_string=None,
                width=None,
                height=None,
                pixel_format=None,
                frame_rate=None,
                duration_seconds=60.0,
                bit_rate=128,
                channels=2,
                channel_layout="stereo",
                sample_rate_hz=48000,
                language="jpn",
                title=None,
                disposition_default=True,
                disposition_forced=False,
                tags=(),
            ),
        )

    return MediaProbe(
        path=str(path),
        format=MediaFormat(
            filename=str(path),
            format_name="matroska,webm",
            format_long_name="Matroska / WebM",
            start_time_seconds=0.0,
            duration_seconds=60.0,
            size_bytes=1024,
            bit_rate=1000,
            tags=(),
        ),
        streams=tuple(streams),
        chapters=(),
    )


def make_service() -> MediaAssetService:
    return MediaAssetService(MagicMock())


@pytest.mark.anyio
async def test_upsert_creates_media_asset_from_probe() -> None:
    service = make_service()
    service.assets.get_for_episode = AsyncMock(return_value=None)
    service.assets.add = AsyncMock()

    episode_id = uuid7()
    processing_job_id = uuid7()
    path = Path("/downloads/example/episode.mkv")

    asset = await service.upsert_from_probe(
        episode_id=episode_id,
        processing_job_id=processing_job_id,
        media_path=str(path),
        probe=make_probe(path),
    )

    assert asset.episode_id == episode_id
    assert asset.processing_job_id == processing_job_id
    assert asset.path == str(path)
    assert asset.format_name == "matroska,webm"
    assert asset.duration_seconds == 60.0
    assert asset.size_bytes == 1024
    assert asset.video_codec == "hevc"
    assert asset.width == 1920
    assert asset.height == 1080
    assert asset.frame_rate == "24000/1001"
    assert asset.audio_codec == "aac"
    assert asset.audio_channels == 2
    assert asset.audio_sample_rate_hz == 48000
    service.assets.add.assert_awaited_once()


@pytest.mark.anyio
async def test_upsert_updates_existing_episode_asset() -> None:
    service = make_service()
    existing = MagicMock()
    service.assets.get_for_episode = AsyncMock(return_value=existing)
    service.assets.add = AsyncMock()

    episode_id = uuid7()
    processing_job_id = uuid7()
    path = Path("/downloads/example/episode.mkv")

    result = await service.upsert_from_probe(
        episode_id=episode_id,
        processing_job_id=processing_job_id,
        media_path=str(path),
        probe=make_probe(path, audio=False),
    )

    assert result is existing
    assert existing.processing_job_id == processing_job_id
    assert existing.path == str(path)
    assert existing.audio_codec is None
    assert existing.audio_channels is None
    assert existing.audio_sample_rate_hz is None
    service.assets.add.assert_not_awaited()


@pytest.mark.anyio
async def test_upsert_rejects_probe_without_video_stream() -> None:
    service = make_service()
    service.assets.get_for_episode = AsyncMock()

    with pytest.raises(MediaAssetValidationError, match="video stream"):
        await service.upsert_from_probe(
            episode_id=uuid7(),
            processing_job_id=uuid7(),
            media_path="/downloads/example/audio.mka",
            probe=make_probe(Path("/downloads/example/audio.mka"), video=False),
        )

    service.assets.get_for_episode.assert_not_awaited()
