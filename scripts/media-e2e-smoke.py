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
from uuid import UUID


class MediaE2ESmokeError(RuntimeError):
    pass


def http_request(
    api_url: str,
    path: str,
    *,
    method: str = "GET",
) -> object:
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}{path}",
        method=method,
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise MediaE2ESmokeError(
            f"{method} {path} returned HTTP {exc.code}: {detail}",
        ) from exc
    except urllib.error.URLError as exc:
        raise MediaE2ESmokeError(
            f"Cannot reach API at {api_url}: {exc}",
        ) from exc


def _require_job(payload: object) -> dict[str, object]:
    if payload is None or not isinstance(payload, dict):
        raise MediaE2ESmokeError(f"Unexpected download job response: {payload!r}")
    return payload


async def ensure_download_job(
    *,
    api_url: str,
    episode_id: UUID,
) -> UUID:
    latest = http_request(
        api_url,
        f"/api/episodes/{episode_id}/download-jobs/latest",
    )

    if isinstance(latest, dict):
        job_id = latest.get("id")
        status = latest.get("status")
        if not isinstance(job_id, str):
            raise MediaE2ESmokeError(
                "Latest download job has no valid id",
            )
        job_uuid = UUID(job_id)
        if status in {"pending", "processing"}:
            print(f"  download: existing job is {status}: {job_uuid}", flush=True)
            return job_uuid
        if status == "completed":
            print(f"  download: existing job is completed: {job_uuid}", flush=True)
            return job_uuid

    created = http_request(
        api_url,
        f"/api/episodes/{episode_id}/download-jobs",
        method="POST",
    )
    job = _require_job(created)
    job_id = job.get("id")
    if not isinstance(job_id, str):
        raise MediaE2ESmokeError("Created download job has no valid id")

    job_uuid = UUID(job_id)
    print(f"  download: job enqueued: {job_uuid}", flush=True)
    return job_uuid


def wait_for_download(
    *,
    api_url: str,
    episode_id: UUID,
    timeout_seconds: float,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    last_signature: tuple[object, ...] | None = None

    while time.monotonic() < deadline:
        payload = _require_job(
            http_request(
                api_url,
                f"/api/episodes/{episode_id}/download-jobs/latest",
            ),
        )
        signature = (
            payload.get("status"),
            payload.get("downloaded_bytes"),
            payload.get("total_bytes"),
            payload.get("attempt_count"),
            payload.get("error_message"),
        )
        if signature != last_signature:
            downloaded = payload.get("downloaded_bytes")
            total = payload.get("total_bytes")
            progress = ""
            if isinstance(downloaded, int) and isinstance(total, int) and total > 0:
                progress = f" {downloaded}/{total} bytes"
            print(
                "  download: "
                f"status={payload.get('status')} "
                f"attempts={payload.get('attempt_count', 0)}"
                f"{progress}",
                flush=True,
            )
            last_signature = signature

        status = payload.get("status")
        if status == "completed":
            return payload
        if status == "failed":
            raise MediaE2ESmokeError(
                "Download failed: "
                f"{payload.get('error_message') or 'unknown error'}",
            )

        time.sleep(2)

    raise MediaE2ESmokeError(
        "Timed out waiting for download after "
        f"{timeout_seconds:.1f}s",
    )


def _require_dict(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise MediaE2ESmokeError(f"Unexpected {label} response: {payload!r}")
    return payload


def get_episode_anime_id(*, api_url: str, episode_id: UUID) -> UUID:
    payload = _require_dict(
        http_request(api_url, f"/api/episodes/{episode_id}"),
        "episode",
    )
    anime_id = payload.get("anime_id")
    if not isinstance(anime_id, str):
        raise MediaE2ESmokeError("Episode response has no valid anime_id")
    return UUID(anime_id)


def wait_for_automatic_pipeline(
    *,
    api_url: str,
    episode_id: UUID,
    anime_id: UUID,
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_signature: tuple[object, ...] | None = None

    while time.monotonic() < deadline:
        payload = _require_dict(
            http_request(api_url, f"/api/animes/{anime_id}/pipeline"),
            "anime pipeline",
        )
        episodes = payload.get("episodes")
        if not isinstance(episodes, list):
            raise MediaE2ESmokeError("Anime pipeline response has no episodes")

        episode = next(
            (
                item
                for item in episodes
                if isinstance(item, dict) and item.get("episode_id") == str(episode_id)
            ),
            None,
        )
        if episode is None:
            raise MediaE2ESmokeError(
                f"Episode {episode_id} is missing from anime pipeline",
            )

        processing = episode.get("processing")
        streaming = episode.get("streaming")
        thumbnail = episode.get("thumbnail")
        if not all(isinstance(value, dict) for value in (processing, streaming, thumbnail)):
            raise MediaE2ESmokeError("Episode pipeline has malformed stage data")

        signature = (
            processing.get("status"),
            processing.get("playable_ready"),
            streaming.get("status"),
            streaming.get("hls_ready"),
            streaming.get("dash_ready"),
            thumbnail.get("status"),
            processing.get("error_message"),
            streaming.get("error_message"),
            thumbnail.get("error_message"),
        )
        if signature != last_signature:
            print(
                "  automatic pipeline: "
                f"processing={processing.get('status')} "
                f"playable={processing.get('playable_ready')} "
                f"streaming={streaming.get('status')} "
                f"hls={streaming.get('hls_ready')} "
                f"dash={streaming.get('dash_ready')} "
                f"thumbnail={thumbnail.get('status')}",
                flush=True,
            )
            last_signature = signature

        if processing.get("status") == "failed":
            raise MediaE2ESmokeError(
                "Media processing failed: "
                f"{processing.get('error_message') or 'unknown error'}",
            )
        if streaming.get("status") == "failed":
            raise MediaE2ESmokeError(
                "Media packaging failed: "
                f"{streaming.get('error_message') or 'unknown error'}",
            )
        if (
            processing.get("playable_ready") is True
            and streaming.get("status") == "completed"
            and streaming.get("hls_ready") is True
            and streaming.get("dash_ready") is True
        ):
            return

        time.sleep(2)

    raise MediaE2ESmokeError(
        "Timed out waiting for automatic media packaging after "
        f"{timeout_seconds:.1f}s",
    )


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run an Episode end-to-end from download through media storage "
            "and HLS/DASH verification."
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
        default=3600.0,
        help="Timeout in seconds for the download and each downstream stage",
    )
    parser.add_argument(
        "--skip-playable",
        action="store_true",
        help="Skip downloading the stored playable MP4 for FFprobe validation",
    )
    args = parser.parse_args()

    if args.timeout <= 0:
        raise MediaE2ESmokeError("timeout must be positive")

    print(f"[media-e2e-smoke] episode={args.episode_id}", flush=True)

    health = http_request(args.api_url, "/api/health")
    if health is None:
        raise MediaE2ESmokeError("API health check returned no response")
    print("  API health: ok", flush=True)

    job_id = await ensure_download_job(
        api_url=args.api_url,
        episode_id=args.episode_id,
    )
    completed_job = wait_for_download(
        api_url=args.api_url,
        episode_id=args.episode_id,
        timeout_seconds=args.timeout,
    )
    print(
        "  download: completed "
        f"job={job_id} bytes={completed_job.get('downloaded_bytes')}",
        flush=True,
    )

    anime_id = get_episode_anime_id(
        api_url=args.api_url,
        episode_id=args.episode_id,
    )
    wait_for_automatic_pipeline(
        api_url=args.api_url,
        episode_id=args.episode_id,
        anime_id=anime_id,
        timeout_seconds=args.timeout,
    )

    smoke_script = Path(__file__).with_name("media-streaming-smoke.py")
    command = [
        sys.executable,
        str(smoke_script),
        str(args.episode_id),
        "--api-url",
        args.api_url,
        "--timeout",
        str(args.timeout),
        "--existing-only",
    ]

    print("  automatic HLS/DASH package verification: starting", flush=True)
    process = await asyncio.to_thread(
        subprocess.run,
        command,
        check=False,
    )
    if process.returncode != 0:
        raise MediaE2ESmokeError(
            "Downstream storage-media-smoke failed "
            f"with exit code {process.returncode}",
        )

    print("[media-e2e-smoke] PASS", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except (MediaE2ESmokeError, ValueError) as exc:
        print(f"[media-e2e-smoke] FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
