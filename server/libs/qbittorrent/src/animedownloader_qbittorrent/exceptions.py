class QBittorrentAPIError(RuntimeError):
    """Base exception for qBittorrent Web API failures."""


class QBittorrentAuthenticationError(QBittorrentAPIError):
    """The qBittorrent API rejected authentication."""


class QBittorrentConnectionError(QBittorrentAPIError):
    """The qBittorrent API could not be reached."""


class QBittorrentAddError(QBittorrentAPIError):
    """qBittorrent rejected a torrent add request."""
