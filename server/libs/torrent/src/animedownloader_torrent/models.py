from dataclasses import dataclass
from enum import StrEnum


class TorrentStatus(StrEnum):
    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    STALLED = "stalled"
    PAUSED = "paused"
    QUEUED = "queued"
    CHECKING = "checking"
    MOVING = "moving"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TorrentInfo:
    id: str
    name: str
    status: TorrentStatus
    progress: float
    downloaded_bytes: int
    total_bytes: int
    save_path: str
    tags: frozenset[str]

    @property
    def is_complete(self) -> bool:
        return self.progress >= 1.0
