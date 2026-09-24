from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest
from animedownloader_anime import Episode
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import get_anime_pipeline_service
from animedownloader_api.pipeline import build_episode_pipeline_summary
from animedownloader_api.schemas import (
    AnimePipelineResponse,
    EpisodePipelineStageStatus,
)
from animedownloader_download import DownloadJob
from animedownloader_media_asset import MediaAsset
from animedownloader_media_processing import (
    MediaPreparationJob,
    MediaProcessingJob,
    MediaStreamingPackage,
    MediaVariant,
)
from animedownloader_storage import LocalStorage


def make_episode() -> Episode:
    anime_id = uuid7()
    now = datetime(2026, 9, 25, tzinfo=UTC)
    return Episode(
        id=uuid7(),
        anime_id=anime_id,
        episode_number=1,
        title="Episode 1",
        source="nyaa",
        source_id="1",
        source_title="Episode 1",
        source_url="https://nyaa.si/view/1",
        torrent_url="https://nyaa.si/download/1.torrent",
        size="1 GiB",
        seeders=10,
        leechers=1,
        downloads=20,
        info_hash="a" * 40,
        download_status="completed",
        conversion_status="completed",
        created_at=now,
        updated_at=now,
    )


def make_completed_pipeline(
    episode: Episode,
) -> tuple[
    DownloadJob,
    MediaProcessingJob,
    MediaAsset,
    MediaPreparationJob,
    MediaVariant,
    MediaStreamingPackage,
]:
    now = datetime(2026, 9, 25, tzinfo=UTC)
    asset = MediaAsset(
        id=uuid7(),
        episode_id=episode.id,
        processing_job_id=uuid7(),
        path="/media/source.mkv",
        metadata_updated_at=now,
        subtitle_tracks_updated_at=now,
        subtitle_tracks_processed_at=now,
        attachments_updated_at=now,
        attachments_processed_at=now,
        thumbnail_status="completed",
        thumbnail_sprite_path="thumbnails/asset/sprite.jpg",
        thumbnail_vtt_path="thumbnails/asset/sprite.vtt",
        thumbnail_updated_at=now,
        created_at=now,
        updated_at=now,
    )
    variant = MediaVariant(
        id=uuid7(),
        media_asset_id=asset.id,
        kind="playable",
        status="completed",
        source_path=asset.path,
        source_metadata_updated_at=asset.metadata_updated_at,
        path="playable/asset/variant.mp4",
        width=1920,
        height=1080,
        duration_seconds=60.0,
        video_codec="hevc",
        audio_codec="aac",
        size_bytes=1_000_000,
        created_at=now,
        updated_at=now,
    )
    preparation = MediaPreparationJob(
        id=uuid7(),
        media_asset_id=asset.id,
        variant_id=variant.id,
        status="completed",
        source_path=asset.path,
        source_metadata_updated_at=asset.metadata_updated_at,
        created_at=now,
        updated_at=now,
    )
    processing = MediaProcessingJob(
        id=uuid7(),
        episode_id=episode.id,
        download_job_id=uuid7(),
        status="completed",
        media_path=asset.path,
        created_at=now,
        updated_at=now,
    )
    download = DownloadJob(
        id=uuid7(),
        episode_id=episode.id,
        status="completed",
        downloaded_bytes=1_000_000,
        total_bytes=1_000_000,
        created_at=now,
        updated_at=now,
    )
    package = MediaStreamingPackage(
        id=uuid7(),
        media_variant_id=variant.id,
        status="completed",
        source_path=variant.path,
        source_variant_updated_at=variant.updated_at,
        hls_master_key="streaming/package/master.m3u8",
        dash_manifest_key="streaming/package/manifest.mpd",
        created_at=now,
        updated_at=now,
    )
    return download, processing, asset, preparation, variant, package


def test_build_pipeline_summary_reports_completed_media_and_streaming() -> None:
    episode = make_episode()
    (
        download,
        processing,
        asset,
        preparation,
        variant,
        package,
    ) = make_completed_pipeline(episode)

    storage = LocalStorage(Path("/tmp/animedownloader-test-media"), "http://test-media")
    summary = build_episode_pipeline_summary(
        episode,
        download_job=download,
        processing_job=processing,
        asset=asset,
        preparation_job=preparation,
        variant=variant,
        package=package,
        storage=storage,
    )

    assert summary.download.status is EpisodePipelineStageStatus.COMPLETED
    assert summary.processing.status is EpisodePipelineStageStatus.COMPLETED
    assert summary.streaming.status is EpisodePipelineStageStatus.COMPLETED
    assert summary.streaming.hls_ready is True
    assert summary.streaming.dash_ready is True
    assert summary.thumbnail.status is EpisodePipelineStageStatus.COMPLETED
    assert summary.thumbnail.url == storage.public_url(asset.thumbnail_sprite_path)
    assert summary.playback_ready is True
    assert summary.active is False


def test_build_pipeline_summary_polls_after_download_before_processing_job_exists() -> None:
    episode = make_episode()
    download, _, asset, preparation, variant, package = make_completed_pipeline(episode)

    summary = build_episode_pipeline_summary(
        episode,
        download_job=download,
        processing_job=None,
        asset=None,
        preparation_job=None,
        variant=None,
        package=None,
        storage=LocalStorage(Path("/tmp/animedownloader-test-media"), "http://test-media"),
    )

    assert summary.download.status is EpisodePipelineStageStatus.COMPLETED
    assert summary.processing.status is EpisodePipelineStageStatus.PENDING
    assert summary.playback_ready is False
    assert summary.active is True


def test_build_pipeline_summary_keeps_playback_ready_while_streaming_runs() -> None:
    episode = make_episode()
    (
        download,
        processing,
        asset,
        preparation,
        variant,
        package,
    ) = make_completed_pipeline(episode)
    package.status = "processing"
    package.hls_master_key = None
    package.dash_manifest_key = None

    summary = build_episode_pipeline_summary(
        episode,
        download_job=download,
        processing_job=processing,
        asset=asset,
        preparation_job=preparation,
        variant=variant,
        package=package,
        storage=LocalStorage(Path("/tmp/animedownloader-test-media"), "http://test-media"),
    )

    assert summary.processing.status is EpisodePipelineStageStatus.COMPLETED
    assert summary.streaming.status is EpisodePipelineStageStatus.PROCESSING
    assert summary.playback_ready is True
    assert summary.active is True


@pytest.mark.anyio
async def test_get_anime_pipeline() -> None:
    episode = make_episode()
    summary = AnimePipelineResponse(
        anime_id=episode.anime_id,
        episodes=[
            build_episode_pipeline_summary(
                episode,
                download_job=None,
                processing_job=None,
                asset=None,
                preparation_job=None,
                variant=None,
                package=None,
                storage=LocalStorage(Path("/tmp/animedownloader-test-media"), "http://test-media"),
            ),
        ],
    )
    service = MagicMock()
    service.get_for_anime = AsyncMock(return_value=summary)

    app = create_app()
    app.dependency_overrides[get_anime_pipeline_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            f"/api/animes/{episode.anime_id}/pipeline",
        )

    assert response.status_code == 200
    assert response.json()["anime_id"] == str(episode.anime_id)
    assert response.json()["episodes"][0]["download"]["status"] == "not_started"
    assert response.json()["episodes"][0]["processing"]["status"] == "not_started"
    service.get_for_anime.assert_awaited_once_with(episode.anime_id)
