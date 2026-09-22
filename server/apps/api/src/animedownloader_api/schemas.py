from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReleaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ReleaseSearchResponse(BaseModel):
    query: str
    items: list[ReleaseResponse]
