from enum import StrEnum


class MediaProcessingJobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaVariantKind(StrEnum):
    PLAYABLE = "playable"


class MediaVariantStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaTranscodingOperation(StrEnum):
    REMUX = "remux"
    TRANSCODE = "transcode"


class MediaPreparationJobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


MediaTranscodingJobStatus = MediaPreparationJobStatus
