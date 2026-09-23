from uuid import UUID

from animedownloader_media import MediaProbe, MediaStream
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import MediaAssetValidationError
from .models import MediaAsset
from .repository import MediaAssetRepository


class MediaAssetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.assets = MediaAssetRepository(session)

    async def get_for_episode(self, episode_id: UUID) -> MediaAsset | None:
        return await self.assets.get_for_episode(episode_id)

    async def upsert_from_probe(
        self,
        *,
        episode_id: UUID,
        processing_job_id: UUID,
        media_path: str,
        probe: MediaProbe,
    ) -> MediaAsset:
        video = _select_primary_stream(probe.video_streams)
        if video is None:
            raise MediaAssetValidationError(
                "Media asset requires at least one video stream",
            )

        audio = _select_primary_stream(probe.audio_streams)
        asset = await self.assets.get_for_episode(episode_id)
        if asset is None:
            asset = MediaAsset(
                episode_id=episode_id,
            )
            await self.assets.add(asset)

        asset.processing_job_id = processing_job_id
        asset.path = media_path
        asset.format_name = probe.format.format_name
        asset.duration_seconds = probe.format.duration_seconds
        asset.size_bytes = probe.format.size_bytes
        asset.video_codec = video.codec_name
        asset.width = video.width
        asset.height = video.height
        asset.frame_rate = video.frame_rate
        asset.audio_codec = audio.codec_name if audio is not None else None
        asset.audio_channels = audio.channels if audio is not None else None
        asset.audio_sample_rate_hz = (
            audio.sample_rate_hz if audio is not None else None
        )
        return asset


def _select_primary_stream(
    streams: tuple[MediaStream, ...],
) -> MediaStream | None:
    if not streams:
        return None

    for stream in streams:
        if stream.disposition_default:
            return stream
    return streams[0]
