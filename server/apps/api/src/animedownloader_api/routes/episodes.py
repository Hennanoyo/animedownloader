from typing import Annotated
from uuid import UUID

from animedownloader_anime import AnimeService, Episode, EpisodeUpdateData
from animedownloader_download import ActiveDownloadJobError, DownloadJob, DownloadJobService
from animedownloader_media_asset import MediaAsset, MediaAssetService
from animedownloader_media_processing import (
    MediaProcessingJob,
    MediaProcessingJobService,
    MediaTranscodingJob,
    MediaTranscodingJobService,
    MediaVariant,
    MediaVariantService,
)
from fastapi import APIRouter, Depends, HTTPException, Response, status

from animedownloader_api.dependencies import (
    get_anime_service,
    get_download_job_service,
    get_download_task_dispatcher,
    get_media_asset_service,
    get_media_processing_job_service,
    get_media_transcoding_job_service,
    get_media_variant_service,
)
from animedownloader_api.schemas import (
    DownloadJobResponse,
    EpisodeResponse,
    EpisodeUpdate,
    MediaAssetResponse,
    MediaProcessingJobResponse,
    MediaTranscodingJobResponse,
    MediaVariantResponse,
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
MediaTranscodingJobServiceDependency = Annotated[
    MediaTranscodingJobService,
    Depends(get_media_transcoding_job_service),
]
MediaVariantServiceDependency = Annotated[
    MediaVariantService,
    Depends(get_media_variant_service),
]


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
    "/{episode_id}/playable-media-transcoding-jobs/latest",
    response_model=MediaTranscodingJobResponse | None,
)
async def get_latest_episode_playable_media_transcoding_job(
    episode_id: UUID,
    anime_service: AnimeServiceDependency,
    media_service: MediaAssetServiceDependency,
    service: MediaTranscodingJobServiceDependency,
) -> MediaTranscodingJob | None:
    await anime_service.get_episode(episode_id)
    asset = await media_service.get_for_episode(episode_id)
    if asset is None:
        return None
    return await service.get_latest_transcoding_job(asset.id)


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