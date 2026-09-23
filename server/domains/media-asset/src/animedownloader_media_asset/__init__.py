from .enums import MediaAttachmentStatus, MediaThumbnailStatus, SubtitleTrackStatus
from .exceptions import MediaAssetValidationError
from .metadata import (
    MediaAssetMetadata,
    MediaAttachmentMetadata,
    MediaChapterMetadata,
    SubtitleTrackMetadata,
)
from .models import MediaAsset, MediaAttachment, MediaChapter, MediaFont, SubtitleTrack
from .service import MediaAssetService

SUBTITLE_PROCESSING_TASK_NAME = "animedownloader.process-subtitle-tracks"
MEDIA_ATTACHMENT_PROCESSING_TASK_NAME = "animedownloader.process-media-attachments"
MEDIA_THUMBNAIL_PROCESSING_TASK_NAME = "animedownloader.process-media-thumbnail"

__all__ = [
    "MEDIA_ATTACHMENT_PROCESSING_TASK_NAME",
    "MediaAsset",
    "MediaAssetMetadata",
    "MediaAssetService",
    "MediaAssetValidationError",
    "MediaAttachment",
    "MediaAttachmentMetadata",
    "MediaAttachmentStatus",
    "MediaThumbnailStatus",
    "MediaChapter",
    "MediaChapterMetadata",
    "MediaFont",
    "MEDIA_THUMBNAIL_PROCESSING_TASK_NAME",
    "SUBTITLE_PROCESSING_TASK_NAME",
    "SubtitleTrack",
    "SubtitleTrackMetadata",
    "SubtitleTrackStatus",
]
