from typing import Annotated
from uuid import UUID

from animedownloader_anime import AnimeService, Episode, EpisodeUpdateData
from animedownloader_download import ActiveDownloadJobError, DownloadJob, DownloadJobService
from animedownloader_media_asset import MediaAsset, MediaAssetService
from animedownloader_media_processing import (
    MediaPreparationJob,
    MediaPreparationJobService,
    MediaProcessingJob,
    MediaProcessingJobService,
    MediaStreamingPackage,
    MediaStreamingPackageService,
    MediaVariantService,
)
from fastapi import APIRouter, Depends, HTTPException, Response, status

from animedownloader_api.dependencies import (
    get_anime_service,
    get_download_job_service,
    get_download_task_dispatcher,
    get_media_asset_service,
    get_media_preparation_job_service,
    get_media_processing_job_service,
    get_media_streaming_package_service,
    get_media_variant_service,
    get_playback_service,
)
from animedownloader_api.playback import PlaybackService
from animedownloader_api.schemas import (
    DownloadJobResponse,
    EpisodeResponse,
    EpisodeUpdate,
    MediaAssetResponse,
    MediaPreparationJobResponse,
    MediaProcessingJobResponse,
    MediaStreamingPackageResponse,
    MediaVariantResponse,
    PlaybackResponse,
)
from animedownloader_api.task_queue import DownloadTaskDispatcher

router = APIRouter(prefix="/api/episodes", tags=["episodes"])
AnimeServiceDependency = Annotated[AnimeService, Depends(get_anime_service)]
DownloadJobServiceDependency = Annotated[
    DownloadJobService,
    Depends(get_download_job_service),
]
DownloadTaskDispatcherDependency = Annotated[
    DownloadTaskDispatcher,
    Depends(get_download_task_dispatcher),
]
MediaAssetServiceDependency = Annotated[
    MediaAssetService,
    Depends(get_media_asset_service),
]
MediaProcessingJobServiceDependency = Annotated[
    MediaProcessingJobService,
    Depends(get_media_processing_job_service),
]
MediaPreparationJobServiceDependency = Annotated[
    MediaPreparationJobService,
    Depends(get_media_preparation_job_service),
]
MediaVariantServiceDependency = Annotated[
    MediaVariantService,
    Depends(get_media_variant_service),
]
MediaStreamingPackageServiceDependency = Annotated[
    MediaStreamingPackageService,
    Depends(get_media_streaming_package_service),
]
PlaybackServiceDependency = Annotated[PlaybackService, Depends(get_playback_service)]


@router.get(
    "/{episode_id}/playback",
    response_model=PlaybackResponse,
)
async def get_episode_playback(
    episode_id: UUID,
    service: PlaybackServiceDependency,
) -> PlaybackResponse:
    return await service.get_episode_playback(episode_id)


@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    episode_id: UUID,
    service: AnimeServiceDependency,
) -> Episode:
    return await service.get_episode(episode_id)


@router.get(
    "/{episode_id}/download-jobs/latest",
    response_model=DownloadJobResponse | None,
)
async def get_latest_episode_download_job(
    episode_id: UUID,
    service: DownloadJobServiceDependency,
) -> DownloadJob | None:
    return await service.get_latest_job(episode_id)


@router.get(
    "/{episode_id}/media",
    response_model=MediaAssetResponse | None,
)
async def get_episode_media(
    episode_id: UUID,
    anime_service: AnimeServiceDependency,
    media_service: MediaAssetServiceDependency,
) -> MediaAsset | None:
    await anime_service.get_episode(episode_id)
    return await media_service.get_for_episode(episode_id)


@router.get(
    "/{episode_id}/media-processing-jobs/latest",
    response_model=MediaProcessingJobResponse | None,
)
async def get_latest_episode_media_processing_job(
    episode_id: UUID,
    service: MediaProcessingJobServiceDependency,
) -> MediaProcessingJob | None:
    return await service.get_latest_job(episode_id)


@router.get(
    "/{episode_id}/playable-media",
    response_model=MediaVariantResponse | None,
)
async def get_episode_playable_media(
    episode_id: UUID,
    anime_service: AnimeServiceDependency,
    media_service: MediaAssetServiceDependency,
    variant_service: MediaVariantServiceDependency,
) -> MediaVariantResponse | None:
    await anime_service.get_episode(episode_id)
    asset = await media_service.get_for_episode(episode_id)
    if asset is None or asset.metadata_updated_at is None:
        return None

    variant = await variant_service.get_playable_variant(asset.id)
    if variant is None:
        return None

    response = MediaVariantResponse.model_validate(variant)
    response.current = variant.is_current(
        source_path=asset.path,
        source_metadata_updated_at=asset.metadata_updated_at,
    )
    return response


@router.get(
    "/{episode_id}/streaming-media",
    response_model=MediaStreamingPackageResponse | None,
)
async def get_episode_streaming_media(
    episode_id: UUID,
    anime_service: AnimeServiceDependency,
    media_service: MediaAssetServiceDependency,
    variant_service: MediaVariantServiceDependency,
    package_service: MediaStreamingPackageServiceDependency,
) -> MediaStreamingPackage | None:
    await anime_service.get_episode(episode_id)
    asset = await media_service.get_for_episode(episode_id)
    if asset is None or asset.metadata_updated_at is None:
        return None

    variant = await variant_service.get_playable_variant(asset.id)
    if variant is None or not variant.ready or variant.path is None:
        return None
    if not variant.is_current(
        source_path=asset.path,
        source_metadata_updated_at=asset.metadata_updated_at,
    ):
        return None

    package = await package_service.get_for_variant(variant.id)
    if package is None or not package.is_current(
        source_path=variant.path,
        source_variant_updated_at=variant.updated_at,
    ):
        return None
    return package


@router.get(
    "/{episode_id}/media-preparation-jobs/latest",
    response_model=MediaPreparationJobResponse | None,
)
async def get_latest_episode_media_preparation_job(
    episode_id: UUID,
    anime_service: AnimeServiceDependency,
    media_service: MediaAssetServiceDependency,
    service: MediaPreparationJobServiceDependency,
) -> MediaPreparationJob | None:
    await anime_service.get_episode(episode_id)
    asset = await media_service.get_for_episode(episode_id)
    if asset is None:
        return None
    return await service.get_latest_job(asset.id)


@router.patch("/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    episode_id: UUID,
    payload: EpisodeUpdate,
    service: AnimeServiceDependency,
) -> Episode:
    return await service.update_episode(
        episode_id,
        EpisodeUpdateData(
            episode_number=payload.episode_number,
            title=payload.title,
            source=payload.source,
            source_id=payload.source_id,
            source_title=payload.source_title,
            source_url=str(payload.source_url) if payload.source_url is not None else None,
            torrent_url=(str(payload.torrent_url) if payload.torrent_url is not None else None),
            size=payload.size,
            seeders=payload.seeders,
            leechers=payload.leechers,
            downloads=payload.downloads,
            info_hash=payload.info_hash,
            download_status=payload.download_status,
            conversion_status=payload.conversion_status,
        ),
    )


@router.post(
    "/{episode_id}/download-jobs",
    response_model=DownloadJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_episode_download_job(
    episode_id: UUID,
    service: DownloadJobServiceDependency,
    dispatcher: DownloadTaskDispatcherDependency,
) -> DownloadJob:
    try:
        job = await service.create_job(episode_id)
    except ActiveDownloadJobError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    try:
        await dispatcher.enqueue(job.id)
    except Exception as exc:
        await service.mark_failed(
            job.id,
            error_message="Failed to enqueue download task.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Download task queue is temporarily unavailable",
        ) from exc

    return job


@router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: UUID,
    service: AnimeServiceDependency,
) -> Response:
    await service.delete_episode(episode_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
