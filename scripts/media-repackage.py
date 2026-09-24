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
from tempfile import TemporaryDirectory
from uuid import UUID

from animedownloader_config import Settings
from animedownloader_database import create_database
from animedownloader_media_asset import MediaAssetService
from animedownloader_media_processing import (
    MediaStreamingPackageService,
    MediaVariantService,
)
from animedownloader_worker.tasks import process_media_packaging
from animedownloader_worker.storage import create_media_storage


class RepackageError(RuntimeError):
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
        raise RepackageError(
            f"GET {path} returned HTTP {exc.code}: {detail}",
        ) from exc
    except urllib.error.URLError as exc:
        raise RepackageError(
            f"Cannot reach API at {api_url}: {exc}",
        ) from exc


async def create_repackage_job(episode_id: UUID) -> UUID:
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        async with database.session_factory() as session:
            asset = await MediaAssetService(session).get_for_episode(episode_id)
            if asset is None or asset.metadata_updated_at is None:
                raise RepackageError(
                    "Episode has no ready MediaAsset metadata. "
                    "Run the normal media-processing pipeline first.",
                )

            variant = await MediaVariantService(session).get_playable_variant(asset.id)
            if variant is None or not variant.ready or variant.path is None:
                raise RepackageError(
                    "Episode has no ready playable media variant. "
                    "Run media preparation first.",
                )

            if not variant.is_current(
                source_path=asset.path,
                source_metadata_updated_at=asset.metadata_updated_at,
            ):
                raise RepackageError(
                    "Playable media variant is stale. "
                    "Run media preparation again before repackaging.",
                )

            service = MediaStreamingPackageService(session)
            active = await service.get_active_job(variant.id)
            if active is not None:
                raise RepackageError(
                    "A media packaging job is already active: "
                    f"{active.id}",
                )

            job = await service.create_job(
                media_variant_id=variant.id,
                force=True,
            )
            if job is None:
                raise RepackageError(
                    "Could not create a forced media packaging job.",
                )

        await process_media_packaging.kiq(str(job.id))
        return job.id
    finally:
        await database.dispose()


def wait_for_job(
    *,
    api_url: str,
    job_id: UUID,
    timeout_seconds: float,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    last_status: str | None = None

    while time.monotonic() < deadline:
        payload = http_get(api_url, f"/api/media-packaging-jobs/{job_id}")
        if not isinstance(payload, dict):
            raise RepackageError(
                f"Unexpected packaging job response: {payload!r}",
            )

        status = str(payload.get("status"))
        if status != last_status:
            print(
                f"  packaging job: status={status} "
                f"attempts={payload.get('attempt_count', 0)}",
                flush=True,
            )
            last_status = status

        if status == "completed":
            return payload
        if status == "failed":
            raise RepackageError(
                "Media packaging failed: "
                f"{payload.get('error_message') or 'unknown error'}",
            )

        time.sleep(2)

    raise RepackageError(
        "Timed out waiting for media packaging job after "
        f"{timeout_seconds:g}s",
    )


async def verify_master_playlist(episode_id: UUID) -> None:
    settings = Settings()
    storage = create_media_storage(settings)
    database = create_database(settings.database_url)

    try:
        async with database.session_factory() as session:
            asset = await MediaAssetService(session).get_for_episode(episode_id)
            if asset is None:
                raise RepackageError("MediaAsset disappeared during repackaging")

            variant = await MediaVariantService(session).get_playable_variant(asset.id)
            if variant is None:
                raise RepackageError("Playable media variant disappeared during repackaging")

            package = await MediaStreamingPackageService(session).get_for_variant(
                variant.id,
            )
            if package is None or not package.is_current(
                source_path=variant.path or "",
                source_variant_updated_at=variant.updated_at,
            ):
                raise RepackageError("Streaming package is not current after repackaging")

            master_key = package.hls_master_key
            if master_key is None:
                raise RepackageError("Completed package has no HLS master key")

        with TemporaryDirectory(prefix="animedownloader-media-repackage-") as directory:
            master_path = Path(directory) / "master.m3u8"
            await storage.materialize(master_key, master_path)
            master = master_path.read_text(encoding="utf-8")
            for line in master.splitlines():
                if line.startswith("#EXT-X-STREAM-INF:"):
                    print(f"  {line}", flush=True)
    finally:
        await database.dispose()


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Force-repackage the current playable media for an Episode "
            "without rerunning download or media preparation."
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
        default=1800.0,
        help="Maximum time to wait for packaging",
    )
    args = parser.parse_args()

    print(
        "[media-repackage] "
        f"episode={args.episode_id}",
        flush=True,
    )

    job_id = await create_repackage_job(args.episode_id)
    print(f"  packaging job enqueued: {job_id}", flush=True)

    await asyncio.to_thread(
        wait_for_job,
        api_url=args.api_url,
        job_id=job_id,
        timeout_seconds=args.timeout,
    )
    await verify_master_playlist(args.episode_id)

    print("[media-repackage] PASS", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except RepackageError as exc:
        print(f"[media-repackage] FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
