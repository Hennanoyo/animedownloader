from pathlib import Path
from uuid import UUID, uuid7

import pytest
from animedownloader_media import FFmpegAttachmentProcessor
from animedownloader_media_asset import MediaAttachmentStatus
from animedownloader_worker.media_attachment_processing import (
    MediaAttachmentContext,
    MediaAttachmentProcessingContext,
    MediaAttachmentProcessingRunner,
)


class FakeState:
    def __init__(self, context: MediaAttachmentProcessingContext) -> None:
        self.context = context
        self.completed: list[tuple[UUID, str, int, UUID | None]] = []
        self.failed: list[tuple[UUID, str]] = []
        self.asset_completed = False
        self.font_id = uuid7()

    async def load(self, asset_id: UUID) -> MediaAttachmentProcessingContext:
        return self.context

    async def mark_processing(self, attachment_id: UUID) -> None:
        return None

    async def mark_completed(
        self,
        attachment_id: UUID,
        *,
        extracted_path: str,
        size_bytes: int,
        font_id: UUID | None = None,
    ) -> None:
        self.completed.append(
            (attachment_id, extracted_path, size_bytes, font_id),
        )

    async def mark_failed(
        self,
        attachment_id: UUID,
        *,
        error_message: str,
    ) -> None:
        self.failed.append((attachment_id, error_message))

    async def mark_asset_complete(self, asset_id: UUID) -> None:
        self.asset_completed = not self.failed

    async def get_or_create_font(
        self,
        *,
        name: str,
        mime_type: str | None,
        sha256: str,
        path: str,
        size_bytes: int,
    ) -> UUID:
        return self.font_id


class StubProcessor(FFmpegAttachmentProcessor):
    async def extract(
        self,
        *,
        media_path: Path,
        attachment_index: int,
        output_path: Path,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"font-data")


def make_context(
    attachment: MediaAttachmentContext,
) -> MediaAttachmentProcessingContext:
    return MediaAttachmentProcessingContext(
        asset_id=uuid7(),
        media_path="/downloads/episode/episode.mkv",
        attachments=(attachment,),
        ready=False,
    )


@pytest.mark.anyio
async def test_runner_extracts_font_and_uses_content_identity(
    tmp_path: Path,
) -> None:
    attachment_id = uuid7()
    context = make_context(
        MediaAttachmentContext(
            id=attachment_id,
            attachment_index=0,
            filename="Example.ttf",
            mime_type="application/x-truetype-font",
            is_font=True,
            status=MediaAttachmentStatus.PENDING,
        ),
    )
    state = FakeState(context)
    runner = MediaAttachmentProcessingRunner(
        state=state,
        processor=StubProcessor(),
        media_root=tmp_path,
    )

    await runner.run(context.asset_id)

    assert state.failed == []
    assert state.asset_completed
    assert len(state.completed) == 1
    assert state.completed[0][0] == attachment_id
    assert state.completed[0][3] == state.font_id
    assert state.completed[0][1].startswith(str(tmp_path / "fonts"))
    assert Path(state.completed[0][1]).read_bytes() == b"font-data"
