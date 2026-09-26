from uuid import UUID

from animedownloader_config import Settings
from animedownloader_database import create_database
from animedownloader_media_processing import (
    MEDIA_PACKAGING_TASK_NAME,
    MEDIA_PREPARATION_TASK_NAME,
    MEDIA_PROCESSING_TASK_NAME,
    MediaPreparationJobService,
    MediaProcessingJobService,
    MediaStreamingPackageService,
)
from taskiq import AsyncBroker, TaskiqEvents, TaskiqState
from taskiq_redis import RedisStreamBroker

from .source_recovery import recover_completed_download_handoffs
