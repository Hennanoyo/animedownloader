from datetime import UTC, datetime
from uuid import uuid7

from animedownloader_media_asset import MediaAsset, MediaThumbnailStatus


def test_media_asset_thumbnail_lifecycle() -> None:
    asset = MediaAsset(
        episode_id=uuid7(),
        processing_job_id=uuid7(),
        path="/downloads/example/episode.mkv",
        thumbnail_status=MediaThumbnailStatus.PENDING.value,
    )

    assert asset.thumbnail_processing_status is MediaThumbnailStatus.PENDING
    assert not asset.thumbnail_ready

    asset.mark_thumbnail_processing()

    assert asset.thumbnail_processing_status is MediaThumbnailStatus.PROCESSING
    assert asset.thumbnail_sprite_path is None
    assert asset.thumbnail_vtt_path is None
    assert asset.thumbnail_updated_at is None

    asset.mark_thumbnail_completed(
        sprite_path="/data/media/thumbnails/sprite.jpg",
        vtt_path="/data/media/thumbnails/sprite.vtt",
    )

    assert asset.thumbnail_processing_status is MediaThumbnailStatus.COMPLETED
    assert asset.thumbnail_ready
    assert asset.thumbnail_updated_at is not None
    assert asset.thumbnail_error_message is None

    asset.mark_thumbnail_failed("thumbnail failed")

    assert asset.thumbnail_processing_status is MediaThumbnailStatus.FAILED
    assert not asset.thumbnail_ready
    assert asset.thumbnail_error_message == "thumbnail failed"

    asset.retry_thumbnail()

    assert asset.thumbnail_processing_status is MediaThumbnailStatus.PENDING
    assert asset.thumbnail_sprite_path is None
    assert asset.thumbnail_vtt_path is None
    assert asset.thumbnail_error_message is None


def test_media_asset_metadata_refresh_invalidates_thumbnail() -> None:
    from animedownloader_media_asset import MediaAssetMetadata

    now = datetime(2026, 9, 24, tzinfo=UTC)
    asset = MediaAsset(
        episode_id=uuid7(),
        processing_job_id=uuid7(),
        path="/downloads/example/episode.mkv",
        thumbnail_status=MediaThumbnailStatus.COMPLETED.value,
        thumbnail_sprite_path="/data/media/thumbnails/sprite.jpg",
        thumbnail_vtt_path="/data/media/thumbnails/sprite.vtt",
        thumbnail_updated_at=now,
    )

    asset.update_metadata(
        MediaAssetMetadata(
            format_name="matroska,webm",
            duration_seconds=60.0,
            size_bytes=1024,
            video_codec="hevc",
            audio_codec="aac",
            width=1920,
            height=1080,
            frame_rate="24000/1001",
        )
    )

    assert asset.thumbnail_processing_status is MediaThumbnailStatus.PENDING
    assert not asset.thumbnail_ready
