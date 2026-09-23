from pathlib import Path

import pytest
from animedownloader_media import (
    MediaChapter,
    MediaFormat,
    MediaProbe,
    MediaStream,
    MediaStreamType,
    PlayableMediaOperation,
    PlayableMediaPlanner,
    PlayableMediaPlanningError,
)


def make_probe(
    *,
    container: str,
    video_codec: str,
    audio_codecs: tuple[str, ...] = ("aac",),
) -> MediaProbe:
    streams = [
        MediaStream(
            index=0,
            codec_type=MediaStreamType.VIDEO,
            codec_name=video_codec,
            codec_long_name=None,
            profile=None,
            codec_tag_string=None,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            frame_rate="24/1",
            duration_seconds=60.0,
            bit_rate=1000000,
            channels=None,
            channel_layout=None,
            sample_rate_hz=None,
            language=None,
            title=None,
            disposition_default=True,
            disposition_forced=False,
            tags=(),
        ),
    ]
    for index, codec in enumerate(audio_codecs, start=1):
        streams.append(
            MediaStream(
                index=index,
                codec_type=MediaStreamType.AUDIO,
                codec_name=codec,
                codec_long_name=None,
                profile=None,
                codec_tag_string=None,
                width=None,
                height=None,
                pixel_format=None,
                frame_rate=None,
                duration_seconds=60.0,
                bit_rate=192000,
                channels=2,
                channel_layout="stereo",
                sample_rate_hz=48000,
                language=None,
                title=None,
                disposition_default=index == 1,
                disposition_forced=False,
                tags=(),
            ),
        )

    return MediaProbe(
        path=str(Path("/tmp/episode.mkv")),
        format=MediaFormat(
            filename="/tmp/episode.mkv",
            format_name=container,
            format_long_name=None,
            start_time_seconds=0.0,
            duration_seconds=60.0,
            size_bytes=1024,
            bit_rate=1000,
            tags=(),
        ),
        streams=tuple(streams),
        chapters=(
            MediaChapter(
                id=1,
                start_time_seconds=0.0,
                end_time_seconds=60.0,
                title="Episode",
            ),
        ),
    )


def test_plans_remux_for_compatible_mp4() -> None:
    probe = make_probe(container="mov,mp4,m4a,3gp,3g2,mj2", video_codec="hevc")

    planner = PlayableMediaPlanner()

    assert planner.plan(probe) is PlayableMediaOperation.REMUX
    assert planner.is_compatible(probe)


def test_plans_transcode_for_incompatible_video() -> None:
    probe = make_probe(
        container="matroska,webm",
        video_codec="mpeg4",
    )

    assert PlayableMediaPlanner().plan(probe) is PlayableMediaOperation.TRANSCODE


def test_plans_transcode_for_incompatible_audio() -> None:
    probe = make_probe(
        container="mp4",
        video_codec="hevc",
        audio_codecs=("opus",),
    )

    assert PlayableMediaPlanner().plan(probe) is PlayableMediaOperation.TRANSCODE


def test_plans_transcode_for_incompatible_container() -> None:
    probe = make_probe(
        container="matroska,webm",
        video_codec="hevc",
    )

    assert PlayableMediaPlanner().plan(probe) is PlayableMediaOperation.TRANSCODE


def test_rejects_probe_without_video() -> None:
    probe = MediaProbe(
        path="/tmp/episode.mkv",
        format=MediaFormat(
            filename="/tmp/episode.mkv",
            format_name="mp4",
            format_long_name=None,
            start_time_seconds=0.0,
            duration_seconds=60.0,
            size_bytes=1024,
            bit_rate=1000,
            tags=(),
        ),
        streams=(),
        chapters=(),
    )

    with pytest.raises(
        PlayableMediaPlanningError,
        match="requires at least one video",
    ):
        PlayableMediaPlanner().plan(probe)
