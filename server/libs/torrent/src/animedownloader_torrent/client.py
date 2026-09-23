from collections.abc import Sequence
from typing import Protocol

from .models import TorrentInfo


class TorrentClient(Protocol):
    async def add(
        self,
        source: str,
        *,
        save_path: str,
        tags: Sequence[str] = (),
    ) -> None: ...

    async def get(self, torrent_id: str) -> TorrentInfo | None: ...

    async def find_by_tag(self, tag: str) -> TorrentInfo | None: ...

    async def pause(self, torrent_id: str) -> None: ...

    async def resume(self, torrent_id: str) -> None: ...

    async def remove(
        self,
        torrent_id: str,
        *,
        delete_files: bool = False,
    ) -> None: ...
