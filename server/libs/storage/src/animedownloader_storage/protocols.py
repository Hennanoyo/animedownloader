from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    async def put_file(
        self,
        source_path: Path,
        object_key: str,
        *,
        content_type: str | None = None,
    ) -> None: ...

    async def materialize(
        self,
        object_key: str,
        destination: Path,
    ) -> Path: ...

    async def exists(self, object_key: str) -> bool: ...

    async def delete(self, object_key: str) -> None: ...

    def public_url(self, object_key: str) -> str: ...
