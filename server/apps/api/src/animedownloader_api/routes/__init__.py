from .animes import router as animes_router
from .download_jobs import router as download_jobs_router
from .episodes import router as episodes_router
from .media_packaging_jobs import router as media_packaging_jobs_router
from .media_preparation_jobs import router as media_preparation_jobs_router
from .media_processing_jobs import router as media_processing_jobs_router
from .releases import router as releases_router

__all__ = [
    "animes_router",
    "download_jobs_router",
    "episodes_router",
    "media_packaging_jobs_router",
    "media_preparation_jobs_router",
    "media_processing_jobs_router",
    "releases_router",
]
