from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .models import MediaProbe, MediaStream


class PlayableMediaPlanningError(RuntimeError):
    pass


class PlayableMediaValidationError(RuntimeError):
    pass


class PlayableMediaOperation(StrEnum):
    REMUX = "remux"
    TRANSCODE = "transcode"


@dataclass(frozen=True, slots=True)
class PlayableMediaProfile:
    container: str = "mp4"
    video_codec: str = "hevc"
    audio_codec: str = "aac"


DEFAULT_PLAYABLE_MEDIA_PROFILE = PlayableMediaProfile()


class PlayableMediaPlanner:
    def __init__(
        self,
        *,
        profile: PlayableMediaProfile = DEFAULT_PLAYABLE_MEDIA_PROFILE,
    ) -> None:
        self.profile = profile

    def plan(self, probe: MediaProbe) -> PlayableMediaOperation:
        video_stream = _primary_video_stream(probe.video_streams)
        if video_stream is None:
            raise PlayableMediaPlanningError("Playable media requires at least one video stream")

        if self.can_remux(probe):
            return PlayableMediaOperation.REMUX
        return PlayableMediaOperation.TRANSCODE

    def validate(self, probe: MediaProbe) -> None:
        video_stream = _primary_video_stream(probe.video_streams)
        if video_stream is None:
            raise PlayableMediaValidationError(
                "Playable output does not contain a video stream",
            )

        if self.is_compatible(probe):
            return

        raise PlayableMediaValidationError(
            "Playable output does not satisfy the target playback profile",
        )

    def can_remux(self, probe: MediaProbe) -> bool:
        video_stream = _primary_video_stream(probe.video_streams)
        if video_stream is None or video_stream.codec_name is None:
            return False

        if video_stream.codec_name.casefold() != self.profile.video_codec:
            return False

        return not any(
            stream.codec_name is None
            or stream.codec_name.casefold() != self.profile.audio_codec
            for stream in probe.audio_streams
        )

    def is_compatible(self, probe: MediaProbe) -> bool:
        if not self.can_remux(probe):
            return False

        format_name = (probe.format.format_name or "").casefold()
        return self.profile.container.casefold() in {
            item.strip() for item in format_name.split(",")
        }


def _primary_video_stream(streams: tuple[MediaStream, ...]) -> MediaStream | None:
    if not streams:
        return None

    return next(
        (stream for stream in streams if stream.disposition_default),
        streams[0],
    )
