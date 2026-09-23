from .enums import MediaAttachmentStatus, SubtitleTrackStatus
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

__all__ = [
    "MEDIA_ATTACHMENT_PROCESSING_TASK_NAME",
    "MediaAsset",
    "MediaAssetMetadata",
    "MediaAssetService",
    "MediaAssetValidationError",
    "MediaAttachment",
    "MediaAttachmentMetadata",
    "MediaAttachmentStatus",
    "MediaChapter",
    "MediaChapterMetadata",
    "MediaFont",
    "SUBTITLE_PROCESSING_TASK_NAME",
    "SubtitleTrack",
    "SubtitleTrackMetadata",
    "SubtitleTrackStatus",
]
