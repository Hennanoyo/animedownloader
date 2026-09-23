from uuid import UUID

from .enums import MediaPreparationJobStatus, MediaProcessingJobStatus


class MediaProcessingJobError(RuntimeError):
    pass


class MediaProcessingJobNotFoundError(MediaProcessingJobError):
    def __init__(self, job_id: UUID) -> None:
        self.job_id = job_id
        super().__init__(f"Media processing job not found: {job_id}")


class InvalidMediaProcessingJobTransitionError(MediaProcessingJobError):
    def __init__(
        self,
        current: MediaProcessingJobStatus,
        target: MediaProcessingJobStatus,
    ) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid media processing job transition: {current.value} -> {target.value}",
        )


class MediaPreparationJobError(MediaProcessingJobError):
    pass


class MediaPreparationJobNotFoundError(MediaPreparationJobError):
    def __init__(self, job_id: UUID) -> None:
        self.job_id = job_id
        super().__init__(f"Media preparation job not found: {job_id}")


class InvalidMediaPreparationJobTransitionError(MediaPreparationJobError):
    def __init__(
        self,
        current: MediaPreparationJobStatus,
        target: MediaPreparationJobStatus,
    ) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid media preparation job transition: {current.value} -> {target.value}",
        )


class MediaPackagingJobError(MediaProcessingJobError):
    pass


class MediaPackagingJobNotFoundError(MediaPackagingJobError):
    def __init__(self, job_id: UUID) -> None:
        self.job_id = job_id
        super().__init__(f"Media packaging job not found: {job_id}")


class InvalidMediaPackagingJobTransitionError(MediaPackagingJobError):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid media packaging job transition: {current} -> {target}",
        )
