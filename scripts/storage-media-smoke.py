#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from animedownloader_config import Settings
from animedownloader_media import parse_cmaf_media_playlist
from animedownloader_storage import Storage, StorageError
from animedownloader_worker.storage import create_media_storage


class SmokeTestError(RuntimeError):
    pass


def http_get(api_url: str, path: str) -> object:
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}{path}",
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise SmokeTestError(
            f"GET {path} returned HTTP {exc.code}: {detail}",
        ) from exc
    except urllib.error.URLError as exc:
        raise SmokeTestError(f"Cannot reach API at {api_url}: {exc}") from exc


def wait_for_playable(
    *,
    api_url: str,
    episode_id: UUID,
    timeout_seconds: float,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    last_status: str | None = None

    while time.monotonic() < deadline:
        payload = http_get(api_url, f"/api/episodes/{episode_id}/playable-media")
        if payload is not None:
            if not isinstance(payload, dict):
                raise SmokeTestError(f"Unexpected playable-media response: {payload!r}")

            status = str(payload.get("status"))
            current = payload.get("current")
            if status == "completed" and current is True and payload.get("path"):
                return payload

            if status != last_status:
                print(f"  playable media: {status}, current={current}")
                last_status = status

        time.sleep(2)

    raise SmokeTestError(
        "Timed out waiting for a current playable media variant after "
        f"{timeout_seconds:g}s",
    )


async def materialize_object(
    storage: Storage,
    object_key: str,
    destination: Path,
    *,
    label: str,
) -> None:
    if not object_key or Path(object_key).is_absolute():
        raise SmokeTestError(
            f"{label} is not a provider-independent object key: {object_key!r}",
        )

    try:
        await storage.materialize(object_key, destination)
    except StorageError as exc:
        raise SmokeTestError(
            f"{label} could not be materialized from storage: "
            f"{object_key}: {exc}",
        ) from exc

    if not destination.is_file() or destination.stat().st_size == 0:
        raise SmokeTestError(
            f"{label} materialized an empty object: {object_key}",
        )


async def verify_playable_media(
    storage: Storage,
    playable: dict[str, object],
    directory: Path,
) -> None:
    path = playable.get("path")
    if not isinstance(path, str) or not path:
        raise SmokeTestError("Playable media has no storage object key")

    target = directory / "playable.mp4"
    await materialize_object(
        storage,
        path,
        target,
        label="playable media",
    )

    process = await asyncio.to_thread(
        subprocess.run,
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=size",
            "-show_entries",
            "stream=codec_type,codec_name",
            "-of",
            "json",
            str(target),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or "unknown ffprobe error"
        raise SmokeTestError(f"Stored playable media failed FFprobe: {detail}")

    try:
        probe = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise SmokeTestError("FFprobe returned invalid JSON") from exc

    streams = probe.get("streams", [])
    video_streams = [
        stream
        for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "video"
    ]
    if not video_streams:
        raise SmokeTestError("Stored playable media contains no video stream")

    print(
        "  playable object: "
        f"{target.stat().st_size} bytes, "
        f"video={video_streams[0].get('codec_name')}",
    )


async def verify_optional_artifacts(
    storage: Storage,
    media: dict[str, object],
    directory: Path,
) -> None:
    optional_paths = [
        ("thumbnail sprite", media.get("thumbnail_sprite_path"), "sprite.jpg"),
        ("thumbnail VTT", media.get("thumbnail_vtt_path"), "sprite.vtt"),
    ]

    for label, object_key, filename in optional_paths:
        if object_key is None:
            continue
        if not isinstance(object_key, str):
            raise SmokeTestError(f"{label} key is not a string")
        target = directory / filename
        await materialize_object(storage, object_key, target, label=label)
        if label == "thumbnail VTT" and not target.read_text(
            encoding="utf-8",
        ).lstrip().startswith("WEBVTT"):
            raise SmokeTestError("Stored thumbnail VTT is invalid")

    subtitle_tracks = media.get("subtitle_tracks")
    if not isinstance(subtitle_tracks, list):
        raise SmokeTestError("Media response has invalid subtitle_tracks")

    for index, track in enumerate(subtitle_tracks):
        if not isinstance(track, dict):
            raise SmokeTestError(f"Invalid subtitle track: {track!r}")
        object_key = track.get("normalized_path")
        if object_key is None:
            continue
        if not isinstance(object_key, str):
            raise SmokeTestError("Subtitle object key is not a string")
        await materialize_object(
            storage,
            object_key,
            directory / f"subtitle-{index}.ass",
            label=f"subtitle track {index}",
        )

    attachments = media.get("attachments")
    if not isinstance(attachments, list):
        raise SmokeTestError("Media response has invalid attachments")

    for index, attachment in enumerate(attachments):
        if not isinstance(attachment, dict):
            raise SmokeTestError(f"Invalid media attachment: {attachment!r}")

        object_key = attachment.get("extracted_path")
        if object_key is not None:
            if not isinstance(object_key, str):
                raise SmokeTestError("Attachment object key is not a string")
            await materialize_object(
                storage,
                object_key,
                directory / f"attachment-{index}",
                label=f"attachment {index}",
            )

        font = attachment.get("font")
        if not isinstance(font, dict):
            continue
        object_key = font.get("path")
        if object_key is None:
            continue
        if not isinstance(object_key, str):
            raise SmokeTestError("Font object key is not a string")
        await materialize_object(
            storage,
            object_key,
            directory / f"font-{index}",
            label=f"font {index}",
        )


async def verify_streaming_package(
    storage: Storage,
    streaming: dict[str, object],
    directory: Path,
) -> None:
    if streaming.get("status") != "completed":
        raise SmokeTestError(
            f"Streaming package is not completed: {streaming.get('status')}",
        )

    master_key = streaming.get("hls_master_key")
    dash_key = streaming.get("dash_manifest_key")
    representations = streaming.get("representations")

    if not isinstance(master_key, str) or not master_key:
        raise SmokeTestError("Streaming package has no HLS master key")
    if not isinstance(dash_key, str) or not dash_key:
        raise SmokeTestError("Streaming package has no DASH manifest key")
    if not isinstance(representations, list) or not representations:
        raise SmokeTestError("Streaming package has no representations")

    master_path = directory / "master.m3u8"
    dash_path = directory / "manifest.mpd"
    await materialize_object(storage, master_key, master_path, label="HLS master")
    await materialize_object(storage, dash_key, dash_path, label="DASH manifest")

    master = master_path.read_text(encoding="utf-8")
    dash = dash_path.read_text(encoding="utf-8")
    if not master.startswith("#EXTM3U"):
        raise SmokeTestError("Stored HLS master is invalid")
    if "<MPD " not in dash:
        raise SmokeTestError("Stored DASH manifest is invalid")

    for index, representation in enumerate(representations):
        if not isinstance(representation, dict):
            raise SmokeTestError(
                f"Invalid streaming representation: {representation!r}",
            )

        quality = representation.get("quality")
        hls_key = representation.get("hls_playlist_key")
        init_key = representation.get("init_segment_key")
        if not all(
            isinstance(value, str) and value
            for value in (quality, hls_key, init_key)
        ):
            raise SmokeTestError(
                f"Incomplete streaming representation {index}: {representation!r}",
            )

        hls_path = directory / f"{quality}-index.m3u8"
        init_path = directory / f"{quality}-init.mp4"
        await materialize_object(
            storage,
            hls_key,
            hls_path,
            label=f"{quality} HLS playlist",
        )
        await materialize_object(
            storage,
            init_key,
            init_path,
            label=f"{quality} init segment",
        )

        playlist = parse_cmaf_media_playlist(
            hls_path.read_text(encoding="utf-8"),
        )
        if not playlist.segments:
            raise SmokeTestError(
                f"Stored {quality} playlist contains no media segments",
            )

        segment_prefix = hls_key.rsplit("/", 1)[0]
        for segment in playlist.segments:
            segment_key = f"{segment_prefix}/{segment.uri}"
            segment_path = directory / f"{quality}-{Path(segment.uri).name}"
            await materialize_object(
                storage,
                segment_key,
                segment_path,
                label=f"{quality} media segment",
            )

        if f"{quality}/index.m3u8" not in master:
            raise SmokeTestError(
                f"HLS master does not reference {quality}/index.m3u8",
            )
        if f'initialization="{quality}/init.mp4"' not in dash:
            raise SmokeTestError(
                f"DASH manifest does not reference {quality}/init.mp4",
            )
        if f'media="{quality}/s/$Number%05d$.m4s"' not in dash:
            raise SmokeTestError(
                f"DASH manifest does not reference {quality}/s/$Number%05d$.m4s",
            )

        print(
            "  streaming representation: "
            f"{quality}, {len(playlist.segments)} media segments",
        )


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that one episode's derived media artifacts are persisted "
            "and readable through the configured storage backend."
        ),
    )
    parser.add_argument("episode_id", type=UUID)
    parser.add_argument(
        "--api-url",
        default="http://api:8000",
        help="API URL from the worker container",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Wait time for a current playable media variant",
    )
    parser.add_argument(
        "--skip-playable",
        action="store_true",
        help="Skip downloading the stored playable MP4 for FFprobe validation",
    )
    args = parser.parse_args()

    settings = Settings()
    storage = create_media_storage(settings)

    print(
        "[storage-media-smoke] "
        f"episode={args.episode_id} backend={settings.storage_backend}",
    )

    if http_get(args.api_url, "/api/health") is None:
        raise SmokeTestError("API health check returned no response")
    print("  API health: ok")

    playable = wait_for_playable(
        api_url=args.api_url,
        episode_id=args.episode_id,
        timeout_seconds=args.timeout,
    )

    media = http_get(
        args.api_url,
        f"/api/episodes/{args.episode_id}/media",
    )
    if not isinstance(media, dict):
        raise SmokeTestError(
            "Episode does not have a materialized MediaAsset",
        )

    variant_key = playable.get("path")
    if not isinstance(variant_key, str) or not variant_key:
        raise SmokeTestError("Playable media has no storage object key")

    streaming = http_get(
        args.api_url,
        f"/api/episodes/{args.episode_id}/streaming-media",
    )
    if not isinstance(streaming, dict):
        raise SmokeTestError(
            "Episode does not have a current completed streaming package",
        )

    with TemporaryDirectory(prefix="animedownloader-storage-media-smoke-") as directory:
        root = Path(directory)

        if args.skip_playable:
            if not await storage.exists(variant_key):
                raise SmokeTestError(
                    f"Playable media object does not exist: {variant_key}",
                )
            print("  playable object: exists")
        else:
            await verify_playable_media(storage, playable, root)

        await verify_optional_artifacts(storage, media, root)
        await verify_streaming_package(storage, streaming, root)

    print("[storage-media-smoke] PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except SmokeTestError as exc:
        print(f"[storage-media-smoke] FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
