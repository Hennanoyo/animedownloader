from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

from sqlalchemy import BigInteger

import pytest
from animedownloader_media_asset import (
    MediaAsset,
    MediaAssetMetadata,
    MediaAssetService,
    MediaAttachmentMetadata,
    MediaAttachmentStatus,
    MediaChapterMetadata,
    SubtitleTrack,
    SubtitleTrackMetadata,
    SubtitleTrackStatus,
)


def make_service() -> MediaAssetService:
    return MediaAssetService(MagicMock())


def make_metadata() -> MediaAssetMetadata:
    return MediaAssetMetadata(
        format_name="matroska,webm",
        duration_seconds=60.0,
        size_bytes=1024,
        video_codec="hevc",
        audio_codec="aac",
        width=1920,
        height=1080,
        frame_rate="24000/1001",
    )


def make_subtitle_tracks() -> tuple[SubtitleTrackMetadata, ...]:
    return (
        SubtitleTrackMetadata(
            stream_index=2,
            language="jpn",
            title="Japanese",
            codec_name="ass",
            source_path=None,
            is_default=True,
            is_forced=False,
        ),
        SubtitleTrackMetadata(
            stream_index=3,
            language="eng",
            title="English",
            codec_name="ass",
            source_path=None,
            is_default=False,
            is_forced=False,
        ),
    )


@pytest.mark.anyio
async def test_upsert_creates_media_asset() -> None:
    service = make_service()
    service.assets.get_for_episode = AsyncMock(return_value=None)

    async def add(asset: MediaAsset) -> None:
        assert asset.processing_job_id is not None
        assert asset.path is not None
        assert asset.metadata_ready
        assert asset.subtitle_tracks_ready
        assert [track.language for track in asset.subtitle_tracks] == ["jpn", "eng"]

    service.assets.add = AsyncMock(side_effect=add)

    episode_id = uuid7()
    processing_job_id = uuid7()
    path = "/downloads/example/episode.mkv"
    metadata = make_metadata()
    subtitle_tracks = make_subtitle_tracks()

    asset = await service.upsert(
        episode_id=episode_id,
        processing_job_id=processing_job_id,
        media_path=path,
        metadata=metadata,
        subtitle_tracks=subtitle_tracks,
    )

    assert asset.episode_id == episode_id
    assert asset.processing_job_id == processing_job_id
    assert asset.path == path
    assert asset.format_name == metadata.format_name
    assert asset.duration_seconds == metadata.duration_seconds
    assert asset.size_bytes == metadata.size_bytes
    assert asset.video_codec == metadata.video_codec
    assert asset.audio_codec == metadata.audio_codec
    assert asset.width == metadata.width
    assert asset.height == metadata.height
    assert asset.frame_rate == metadata.frame_rate
    assert asset.metadata_updated_at is not None
    assert asset.subtitle_tracks_updated_at is not None
    assert [(track.stream_index, track.codec_name) for track in asset.subtitle_tracks] == [
        (2, "ass"),
        (3, "ass"),
    ]
    service.assets.add.assert_awaited_once_with(asset)


@pytest.mark.anyio
async def test_upsert_updates_existing_episode_asset() -> None:
    service = make_service()
    existing = MagicMock()
    service.assets.get_for_episode = AsyncMock(return_value=existing)
    service.assets.add = AsyncMock()
    metadata = make_metadata()
    subtitle_tracks = make_subtitle_tracks()

    episode_id = uuid7()
    processing_job_id = uuid7()
    path = "/downloads/example/episode.mkv"

    result = await service.upsert(
        episode_id=episode_id,
        processing_job_id=processing_job_id,
        media_path=path,
        metadata=metadata,
        subtitle_tracks=subtitle_tracks,
    )

    assert result is existing
    assert existing.processing_job_id == processing_job_id
    assert existing.path == path
    existing.update_metadata.assert_called_once_with(metadata)
    existing.update_subtitle_tracks.assert_called_once_with(subtitle_tracks)
    service.assets.add.assert_not_awaited()


def test_subtitle_track_lifecycle() -> None:
    track = SubtitleTrack(
        media_asset_id=uuid7(),
        stream_index=2,
        language="jpn",
        title="Japanese",
        codec_name="subrip",
        source_path=None,
        status=SubtitleTrackStatus.PENDING.value,
    )

    assert track.processing_status is SubtitleTrackStatus.PENDING

    track.mark_processing()
    assert track.processing_status is SubtitleTrackStatus.PROCESSING
    assert track.error_message is None

    track.mark_failed("conversion failed")
    assert track.processing_status is SubtitleTrackStatus.FAILED
    assert track.error_message == "conversion failed"

    track.retry()
    assert track.processing_status is SubtitleTrackStatus.PENDING
    assert track.normalized_path is None
    assert track.normalized_format is None
    assert track.error_message is None

    track.mark_processing()
    track.mark_completed(
        normalized_path="/data/media/subtitles/track.ass",
        normalized_format="ass",
    )
    assert track.processing_status is SubtitleTrackStatus.COMPLETED
    assert track.normalized_path == "/data/media/subtitles/track.ass"



def test_media_chapter_id_uses_bigint() -> None:
    assert isinstance(MediaChapter.__table__.c.chapter_id.type, BigInteger)


def test_media_asset_chapters_and_attachments_state() -> None:
    asset = MediaAsset(
        episode_id=uuid7(),
        processing_job_id=uuid7(),
        path="/downloads/example/episode.mkv",
    )
    asset.update_chapters(
        (
            MediaChapterMetadata(
                chapter_index=0,
                id=1,
                start_time_seconds=0.0,
                end_time_seconds=30.0,
                title="Intro",
            ),
        ),
    )
    asset.update_attachments(
        (
            MediaAttachmentMetadata(
                attachment_index=0,
                stream_index=4,
                filename="Example.ttf",
                mime_type="application/x-truetype-font",
                description="Example",
                is_font=True,
            ),
        ),
    )

    assert asset.chapters_ready
    assert asset.attachments_ready
    assert not asset.attachment_processing_ready
    assert asset.attachments[0].processing_status is MediaAttachmentStatus.PENDING

    asset.attachments[0].mark_completed(
        extracted_path="/data/media/fonts/aa/aa.ttf",
        size_bytes=10,
    )
    asset.mark_attachment_processing_complete()

    assert asset.attachment_processing_ready
