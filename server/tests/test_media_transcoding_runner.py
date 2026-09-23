from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid7

import pytest
from animedownloader_media import (
    MediaFormat,
    MediaProbe,
    MediaStream,
    MediaStreamType,
    PlayableMediaOperation,
    PlayableMediaPlanner,
    PlayableMediaProcessingResult,
)
from animedownloader_media_processing import (
    MediaTranscodingJobStatus,
    MediaTranscodingOperation,
)
from animedownloader_worker.media_transcoding import (
    MediaTranscodingContext,
    MediaTranscodingRunner,
)


@dataclass
class FakeState:
    context: MediaTranscodingContext
    transitions: list[str] = field(default_factory=lambda: list[str]())
    completed_path: Path | None = None
    failed_message: str | None = None

    async def load(self, job_id: UUID) -> MediaTranscodingContext:
        return self.context

    async def mark_processing(
        self,
        job_id: UUID,
        operation: MediaTranscodingOperation,
    ) -> None:
        self.transitions.append(operation.value)
        self.context = MediaTranscodingContext(
            job_id=self.context.job_id,
            asset_id=self.context.asset_id,
            source_path=self.context.source_path,
            source_metadata_updated_at=self.context.source_metadata_updated_at,
            status=MediaTranscodingJobStatus.PROCESSING,
            operation=operation,
            variant_id=self.context.variant_id,
        )

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        output_path: Path,
        probe: MediaProbe,
    ) -> None:
        self.completed_path = output_path
        self.context = MediaTranscodingContext(