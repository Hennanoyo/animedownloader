#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import UUID

from animedownloader_config import Settings
from animedownloader_database import create_database
from animedownloader_media import parse_cmaf_media_playlist
from animedownloader_media_asset import MediaAssetService
from animedownloader_media_processing import (
    MediaStreamingPackageService,
    MediaVariantService,
)
from animedownloader_worker.tasks import process_media_packaging


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


def resolve_media_path(media_root: Path, key: str) -> Path:
    root = media_root.resolve()
    path = (media_root / key).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SmokeTestError(f"Media key escapes MEDIA_ROOT: {key}") from exc
    return path


def wait_for_packaging_job(
    *,
    api_url: str,
    job_id: UUID,
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_status: str | None = None

    while time.monotonic() < deadline:
        payload = http_get(api_url, f"/api/media-packaging-jobs/{job_id}")
        if not isinstance(payload, dict):
            raise SmokeTestError(f"Unexpected packaging job response: {payload!r}")

        status = str(payload.get("status"))
        if status != last_status:
            print(f"  packaging job: {status}")
            last_status = status

        if status == "completed":
            return
        if status == "failed":
            raise SmokeTestError(
                f"Packaging failed: {payload.get('error_message')}",
            )

        time.sleep(2)

    raise SmokeTestError(
        f"Timed out waiting for packaging job after {timeout_seconds:g}s",
    )


async def ensure_packaging_job(episode_id: UUID) -> UUID | None:
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        async with database.session_factory() as session:
            asset = await MediaAssetService(session).get_for_episode(episode_id)
            if asset is None or asset.metadata_updated_at is None:
                raise SmokeTestError(
                    "Episode has no media asset with metadata. "
                    "Run the normal media-processing pipeline first.",
                )

            variant = await MediaVariantService(session).get_playable_variant(asset.id)
            if variant is None or not variant.ready or variant.path is None:
                raise SmokeTestError(
                    "Episode has no ready playable media variant. "
                    "Run media preparation first.",
                )

            if not variant.is_current(
                source_path=asset.path,
                source_metadata_updated_at=asset.metadata_updated_at,
            ):
                raise SmokeTestError(
                    "Playable media variant is stale. "
                    "Run media preparation again.",
                )

            package_service = MediaStreamingPackageService(session)
            job = await package_service.create_job(media_variant_id=variant.id)
            if job is None:
                existing_job = await package_service.get_latest_job(variant.id)
                if existing_job is not None and existing_job.status in {
                    "pending",
                    "processing",
                }:
                    return existing_job.id
                return None

        await process_media_packaging.kiq(str(job.id))
        print(f"  packaging job enqueued: {job.id}")
        return job.id
    finally:
        await database.dispose()


def verify_streaming_package(
    *,
    api_url: str,
    media_root: Path,
    episode_id: UUID,
) -> None:
    payload = http_get(
        api_url,
        f"/api/episodes/{episode_id}/streaming-media",
    )
    if payload is None:
        raise SmokeTestError(
            "Streaming package is not ready.",
        )
    if not isinstance(payload, dict):
        raise SmokeTestError(f"Unexpected streaming response: {payload!r}")

    if payload.get("status") != "completed":
        raise SmokeTestError(
            f"Streaming package is not completed: {payload.get('status')}",
        )

    master_key = payload.get("hls_master_key")
    dash_key = payload.get("dash_manifest_key")
    representations = payload.get("representations")

    if not isinstance(master_key, str) or not master_key:
        raise SmokeTestError("Streaming package has no HLS master key")
    if not isinstance(dash_key, str) or not dash_key:
        raise SmokeTestError("Streaming package has no DASH manifest key")
    if not isinstance(representations, list) or not representations:
        raise SmokeTestError("Streaming package has no representations")

    master_path = resolve_media_path(media_root, master_key)
    dash_path = resolve_media_path(media_root, dash_key)
    if not master_path.is_file():
        raise SmokeTestError(f"Missing HLS master: {master_path}")
    if not dash_path.is_file():
        raise SmokeTestError(f"Missing DASH manifest: {dash_path}")

    master = master_path.read_text(encoding="utf-8")
    dash = dash_path.read_text(encoding="utf-8")
    if not master.startswith("#EXTM3U"):
        raise SmokeTestError("HLS master is invalid")
    if "<MPD " not in dash:
        raise SmokeTestError("DASH manifest is invalid")

    for representation in representations:
        if not isinstance(representation, dict):
            raise SmokeTestError(f"Invalid representation: {representation!r}")

        quality = representation.get("quality")
        hls_key = representation.get("hls_playlist_key")
        init_key = representation.get("init_segment_key")
        segment_key = representation.get("segment_directory_key")
        if not all(
            isinstance(value, str) and value
            for value in (quality, hls_key, init_key, segment_key)
        ):
            raise SmokeTestError(f"Incomplete representation: {representation!r}")

        hls_path = resolve_media_path(media_root, hls_key)
        init_path = resolve_media_path(media_root, init_key)
        segment_dir = resolve_media_path(media_root, segment_key)
        if not hls_path.is_file():
            raise SmokeTestError(f"Missing HLS media playlist: {hls_path}")
        if not init_path.is_file():
            raise SmokeTestError(f"Missing init segment: {init_path}")
        if not segment_dir.is_dir():
            raise SmokeTestError(f"Missing segment directory: {segment_dir}")

        playlist = parse_cmaf_media_playlist(
            hls_path.read_text(encoding="utf-8"),
        )
        for segment in playlist.segments:
            segment_path = resolve_media_path(
                media_root,
                str(Path(hls_key).parent / segment.uri),
            )
            if not segment_path.is_file():
                raise SmokeTestError(f"Missing media segment: {segment_path}")

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
            "  representation verified: "
            f"{quality}, {len(playlist.segments)} media segments",
        )


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify an episode's current playable media through CMAF packaging "
            "and HLS/DASH output."
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
        default=180.0,
        help="Packaging timeout in seconds",
    )
    args = parser.parse_args()

    episode_id: UUID = args.episode_id
    settings = Settings()

    print(f"[media-smoke] episode={episode_id}")
    health = http_get(args.api_url, "/api/health")
    if health is None:
        raise SmokeTestError("API health check returned no response")
    print("  API health: ok")

    playable = http_get(
        args.api_url,
        f"/api/episodes/{episode_id}/playable-media",
    )
    if not isinstance(playable, dict):
        raise SmokeTestError(
            "Episode has no playable media variant. "
            "Run media preparation first.",
        )
    if playable.get("ready") is not True or playable.get("current") is not True:
        raise SmokeTestError("Playable media is not current and ready")
    print(
        "  playable media: "
        f"{playable.get('width')}x{playable.get('height')} "
        f"{playable.get('video_codec')}",
    )

    job_id = await ensure_packaging_job(episode_id)
    if job_id is not None:
        await asyncio.to_thread(
            wait_for_packaging_job,
            api_url=args.api_url,
            job_id=job_id,
            timeout_seconds=args.timeout,
        )
    else:
        print("  packaging job: existing current package")

    verify_streaming_package(
        api_url=args.api_url,
        media_root=settings.media_root,
        episode_id=episode_id,
    )
    print("[media-smoke] PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except SmokeTestError as exc:
        print(f"[media-smoke] FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
