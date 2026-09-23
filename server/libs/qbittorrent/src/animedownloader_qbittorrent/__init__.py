from .client import QBittorrentClient
from .exceptions import (
    QBittorrentAddError,
    QBittorrentAPIError,
    QBittorrentAuthenticationError,
    QBittorrentConnectionError,
)

__all__ = [
    "QBittorrentAPIError",
    "QBittorrentAddError",
    "QBittorrentAuthenticationError",
    "QBittorrentClient",
    "QBittorrentConnectionError",
]
