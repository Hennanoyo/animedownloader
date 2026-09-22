from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Release:
    source: str
    id: str
    title: str
    page_url: str
    torrent_url: str
    published_at: datetime | None
    size: str | None
    seeders: int | None
    leechers: int | None
    downloads: int | None
    info_hash: str | None
