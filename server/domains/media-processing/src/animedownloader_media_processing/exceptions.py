from uuid import UUID

from .enums import MediaProcessingJobStatus


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
