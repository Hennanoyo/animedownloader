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
    InvalidMediaPreparationJobTransitionError,
    InvalidMediaProcessingJobTransitionError,
    InvalidMediaTranscodingJobTransitionError,
    MediaPreparationJobNotFoundError,
    MediaProcessingJobNotFoundError,
    MediaTranscodingJobNotFoundError,
)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from animedownloader_api.media_processing_queue import MediaProcessingTaskDispatcher
from animedownloader_api.routes import (
    animes_router,
    download_jobs_router,
    episodes_router,
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

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        await task_broker.startup()
        try:
            yield
        finally:
            await task_broker.shutdown()
            await database.dispose()

    app = FastAPI(
        title="AnimeDownloader API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.database = database
    app.state.download_task_dispatcher = task_dispatcher
    app.state.media_processing_task_dispatcher = media_processing_task_dispatcher
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
    app.add_exception_handler(MediaPreparationJobNotFoundError, _not_found_handler)
    app.add_exception_handler(MediaProcessingJobNotFoundError, _not_found_handler)
    app.add_exception_handler(MediaTranscodingJobNotFoundError, _not_found_handler)
    app.add_exception_handler(
        InvalidMediaPreparationJobTransitionError,
        _duplicate_episode_handler,
    )
    app.add_exception_handler(
        InvalidMediaProcessingJobTransitionError,
        _duplicate_episode_handler,
    )
    app.add_exception_handler(
        InvalidMediaTranscodingJobTransitionError,
        _duplicate_episode_handler,
    )
    app.add_exception_handler(DuplicateEpisodeError, _duplicate_episode_handler)
    app.include_router(animes_router)
    app.include_router(episodes_router)
    app.include_router(download_jobs_router)
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
