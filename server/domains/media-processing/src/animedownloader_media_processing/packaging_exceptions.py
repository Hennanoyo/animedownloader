from uuid import UUID


class MediaPackagingJobNotFoundError(LookupError):
    def __init__(self, job_id: UUID) -> None:
        super().__init__(f"Media packaging job not found: {job_id}")


class MediaStreamingPackageNotFoundError(LookupError):
    def __init__(self, package_id: UUID) -> None:
        super().__init__(f"Media streaming package not found: {package_id}")


class MediaStreamingVariantNotFoundError(LookupError):
    def __init__(self, variant_id: UUID) -> None:
        super().__init__(f"Playable media variant not found: {variant_id}")


class InvalidMediaPackagingJobTransitionError(ValueError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Invalid media packaging job transition: {current} -> {target}",
        )
