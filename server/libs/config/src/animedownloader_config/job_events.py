from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

JOB_PROGRESS_CHANNEL = "animedownloader:job-progress"


class JobProgressEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    type: Literal["job.progress"] = "job.progress"
    job_type: str = Field(min_length=1, max_length=64)
    job_id: UUID
    status: str = Field(min_length=1, max_length=64)
    progress_percent: float | None = Field(default=None, ge=0, le=100)
    downloaded_bytes: int | None = Field(default=None, ge=0)
    total_bytes: int | None = Field(default=None, ge=0)
    error_message: str | None = Field(default=None, max_length=2000)
    emitted_at: datetime


class JobProgressReadyEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    type: Literal["job.ready"] = "job.ready"
    job_type: str = Field(min_length=1, max_length=64)
    emitted_at: datetime
