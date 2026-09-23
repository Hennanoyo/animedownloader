class StorageError(RuntimeError):
    """Raised when a storage operation cannot be completed."""


class StorageObjectNotFoundError(StorageError):
    """Raised when a requested storage object does not exist."""
