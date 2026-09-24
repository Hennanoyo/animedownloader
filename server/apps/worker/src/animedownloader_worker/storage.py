from animedownloader_config import Settings
from animedownloader_storage import Storage, create_storage


def create_media_storage(settings: Settings) -> Storage:
    return create_storage(
        backend=settings.storage_backend,
        local_root=settings.media_root,
        internal_url=settings.storage_internal_url,
        public_url=settings.storage_public_url,
    )
