from uuid import UUID

from .enums import DownloadJobStatus


class DownloadJobNotFoundError(Exception):
    def __init__(self, job_id: UUID) -> None:
        super().__init__(f"Download job not found: {job_id}")
        self.job_id = job_id


class InvalidDownloadJobTransitionError(Exception):
    def __init__(
        self,
        current: DownloadJobStatus,
        target: DownloadJobStatus,
    ) -> None:
        super().__init__(f"Invalid download job transition: {current.value} -> {target.value}")
        self.current = current
        self.target = target


class ActiveDownloadJobError(Exception):
    def __init__(self, episode_id: UUID, job_id: UUID) -> None:
        super().__init__(
            f"Episode {episode_id} already has active download job: {job_id}"
        )
        self.episode_id = episode_id
        self.job_id = job_id
