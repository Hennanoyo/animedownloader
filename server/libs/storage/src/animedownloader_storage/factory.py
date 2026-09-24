from pathlib import Path
from typing import Literal

from .adapters import LocalStorage, SeaweedFSStorage
from .exceptions import StorageError
from .protocols import Storage

StorageBackend = Literal["local", "seaweedfs"]


def create_storage(
    *,
    backend: StorageBackend,
    local_root: Path,
    internal_url: str,
    public_url: str,
    timeout_seconds: float = 60.0,
) -> Storage:
    if backend == "local":
        return LocalStorage(local_root, public_url)
    if backend == "seaweedfs":
        return SeaweedFSStorage(
            internal_url,
            public_url,
            timeout_seconds=timeout_seconds,
        )
    raise StorageError(f"Unsupported storage backend: {backend}")
