from .animes import router as animes_router
from .episodes import router as episodes_router
from .releases import router as releases_router

__all__ = ["animes_router", "episodes_router", "releases_router"]
