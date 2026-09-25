from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from animedownloader_anime import (
    AnimeNotFoundError,
    DuplicateEpisodeError,
    EpisodeNotFoundError,
)
from animedownloader_config import Settings
from animedownloader_database import create_database
from animedownloader_download import (
    DownloadJobActiveError,
    DownloadJobNotFoundError,
    InvalidDownloadJobTransitionError,
)
from animedownloader_media_processing import (
    InvalidMediaPackagingJobTransitionError,
    InvalidMediaPreparationJobTransitionError,
    InvalidMediaProcessingJobTransitionError,
    MediaPackagingJobNotFoundError,
    MediaPreparationJobNotFoundError,
    MediaProcessingJobNotFoundError,
    MediaStreamingPackageNotFoundError,
)
from animedownloader_storage import create_storage
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from animedownloader_api.job_progress import JobProgressHub
from animedownloader_api.media_processing_queue import MediaProcessingTaskDispatcher
from animedownloader_api.routes import (
    anime_pipeline_router,
    animes_router,
    download_jobs_router,
    job_events_router,
    episode_pipeline_router,
    episodes_router,
    media_packaging_jobs_router,
    media_preparation_jobs_router,
    media_processing_jobs_router,
    releases_router,
)
from animedownloader_api.task_queue import (
    DownloadTaskDispatcher,
    create_task_broker,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    database = create_database(app_settings.database_url)
    task_broker = create_task_broker(app_settings.redis_url)
    task_dispatcher = DownloadTaskDispatcher(task_broker)
    media_processing_task_dispatcher = MediaProcessingTaskDispatcher(task_broker)
    job_progress_hub = JobProgressHub(app_settings.redis_url)
    media_storage = create_storage(
        backend=app_settings.storage_backend,
        local_root=app_settings.media_root,
        internal_url=app_settings.storage_internal_url,
        public_url=app_settings.storage_public_url,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        await task_broker.startup()
        await job_progress_hub.start()
        try:
            yield
        finally:
            await job_progress_hub.stop()
            await task_broker.shutdown()
            await database.dispose()

    app = FastAPI(
        title="AnimeDownloader API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.database = database
    app.state.download_task_dispatcher = task_dispatcher
    app.state.job_progress_hub = job_progress_hub
    app.state.media_processing_task_dispatcher = media_processing_task_dispatcher
    app.state.media_storage = media_storage
    app.state.settings = app_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AnimeNotFoundError, _not_found_handler)
    app.add_exception_handler(EpisodeNotFoundError, _not_found_handler)
    app.add_exception_handler(DownloadJobActiveError, _duplicate_episode_handler)
    app.add_exception_handler(DownloadJobNotFoundError, _not_found_handler)
    app.add_exception_handler(InvalidDownloadJobTransitionError, _duplicate_episode_handler)
    app.add_exception_handler(MediaPackagingJobNotFoundError, _not_found_handler)
    app.add_exception_handler(MediaPreparationJobNotFoundError, _not_found_handler)
    app.add_exception_handler(MediaProcessingJobNotFoundError, _not_found_handler)
    app.add_exception_handler(
        InvalidMediaPackagingJobTransitionError,
        _duplicate_episode_handler,
    )
    app.add_exception_handler(
        InvalidMediaPreparationJobTransitionError,
        _duplicate_episode_handler,
    )
    app.add_exception_handler(
        MediaStreamingPackageNotFoundError,
        _not_found_handler,
    )
    app.add_exception_handler(
        InvalidMediaProcessingJobTransitionError,
        _duplicate_episode_handler,
    )
    app.add_exception_handler(DuplicateEpisodeError, _duplicate_episode_handler)
    app.include_router(animes_router)
    app.include_router(anime_pipeline_router)
    app.include_router(episode_pipeline_router)
    app.include_router(episodes_router)
    app.include_router(download_jobs_router)
    app.include_router(job_events_router)
    app.include_router(media_packaging_jobs_router)
    app.include_router(media_preparation_jobs_router)
    app.include_router(media_processing_jobs_router)
    app.include_router(releases_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "api"}

    return app


async def _not_found_handler(
    _: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def _duplicate_episode_handler(
    _: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


app = create_app()
