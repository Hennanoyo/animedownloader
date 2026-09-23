from uuid import UUID

from .exceptions import (
    InvalidMediaPackagingJobTransitionError,
    MediaPackagingJobError,
)

from .exceptions import (
    InvalidMediaPackagingJobTransitionError,
    MediaPackagingJobError,
)


class MediaPackagingJobNotFoundError(MediaPackagingJobError):
    def __init__(self, job_id: UUID) -> None:
        super().__init__(f"Media packaging job not found: {job_id}")


class MediaStreamingPackageNotFoundError(MediaPackagingJobError):
    def __init__(self, package_id: UUID) -> None:
        super().__init__(f"Media streaming package not found: {package_id}")


class MediaStreamingVariantNotFoundError(MediaPackagingJobError):
    def __init__(self, variant_id: UUID) -> None:
        super().__init__(f"Playable media variant not found: {variant_id}")


