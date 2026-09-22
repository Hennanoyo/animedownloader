from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from animedownloader_anime import (
    AnimeNotFoundError,
    DuplicateEpisodeError,
    EpisodeNotFoundError,
)
from animedownloader_config import Settings
from animedownloader_database import Database, create_database
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from animedownloader_api.routes import animes_router, episodes_router, releases_router


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    database = create_database(app_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await database.dispose()

    app = FastAPI(
        title="AnimeDownloader API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.database = database

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AnimeNotFoundError, _not_found_handler)
    app.add_exception_handler(EpisodeNotFoundError, _not_found_handler)
    app.add_exception_handler(DuplicateEpisodeError, _duplicate_episode_handler)
    app.include_router(animes_router)
    app.include_router(episodes_router)
    app.include_router(releases_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "api"}

    return app


async def _not_found_handler(
    _: Request,
    exc: AnimeNotFoundError | EpisodeNotFoundError,
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def _duplicate_episode_handler(
    _: Request,
    exc: DuplicateEpisodeError,
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


app = create_app()
