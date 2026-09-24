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

from redis import Redis

from animedownloader_config import Settings
from animedownloader_database import create_database
from animedownloader_download import DownloadJobService, DownloadJobStatus
from animedownloader_media import parse_cmaf_media_playlist
from animedownloader_media_asset import MediaAssetService
from animedownloader_media_processing import (
    MediaPackagingJobStatus,
    MediaPreparationJobService,
    MediaPreparationJobStatus,
    MediaProcessingJobService,
    MediaProcessingJobStatus,
    MediaStreamingPackageService,
    MediaVariantService,
)
from animedownloader_storage import Storage, StorageError
from animedownloader_worker.storage import create_media_storage
from animedownloader_worker.tasks import (
    process_media_attachments,
    process_media_job,
    process_media_packaging,
    process_media_preparation,
    process_subtitle_tracks,
)


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


def _require_object(payload: object, label: str) -> dict[str, object]:
    if payload is None:
        raise SmokeTestError(f"{label} returned no job")
    if not isinstance(payload, dict):
        raise SmokeTestError(f"Unexpected {label} response: {payload!r}")
    return payload


def _validate_preparation_payload(payload: object) -> dict[str, object] | None:
    if payload is None:
        return None

    preparation = _require_object(
        payload,
        "media-preparation-jobs/latest",
    )
    fields = set(preparation)
    if {
        "download_job_id",
        "media_path",
        "probe_metadata",
    }.issubset(fields) and "media_asset_id" not in fields:
        raise SmokeTestError(
            "GET /media-preparation-jobs/latest returned a "
            "MediaProcessingJob-shaped payload. "
            "Check the running API image/source and the requested endpoint.",
        )

    required = {
        "media_asset_id",
        "variant_id",
        "status",
        "source_path",
        "source_metadata_updated_at",
    }
    missing = sorted(required - fields)
    if missing:
        raise SmokeTestError(
            "GET /media-preparation-jobs/latest returned an unexpected payload; "
            f"missing fields: {', '.join(missing)}",
        )
    return preparation


def _state_summary(
    *,
    playable: dict[str, object] | None,
    preparation: dict[str, object] | None,
    processing: dict[str, object] | None,
) -> str:
    def describe(
        payload: dict[str, object] | None,
        *,
        include_current: bool = False,
    ) -> str:
        if payload is None:
            return "none"
        status = str(payload.get("status"))
        error = payload.get("error_message")
        summary = status
        if include_current:
            summary += f", current={payload.get('current')}"
        if error:
            summary += f", error={error!r}"
        return summary

    return (
        "  state: "
        f"processing={describe(processing)}, "
        f"preparation={describe(preparation)}, "
        f"playable={describe(playable, include_current=True)}"
    )


def _format_size(size: int) -> str:
    units = ("B", "KiB", "MiB", "GiB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{size}B"


def _active_ffmpeg_processes() -> list[str]:
    processes: list[str] = []
    for process_dir in Path("/proc").glob("[0-9]*"):
        try:
            name = process_dir.joinpath("comm").read_text(
                encoding="utf-8",
            ).strip()
            if name != "ffmpeg":
                continue
            raw_cmdline = process_dir.joinpath("cmdline").read_bytes()
            command = raw_cmdline.replace(b"\0", b" ").decode(
                "utf-8",
                errors="replace",
            ).strip()
            processes.append(f"pid={process_dir.name} command={command}")
        except (OSError, UnicodeDecodeError):
            continue
    return processes


def _temporary_media_outputs() -> list[str]:
    outputs: list[str] = []
    for directory in Path("/tmp").glob("animedownloader-preparation-*"):
        for pattern in ("playable/**/*.mp4", "thumbnails/**/*.jpg"):
            for path in sorted(directory.glob(pattern)):
                try:
                    outputs.append(
                        f"{path.name}={_format_size(path.stat().st_size)}",
                    )
                except OSError:
                    continue
    return outputs


def _redis_queue_diagnostics(
    settings: Settings,
    *,
    job_ids: set[str],
) -> list[str]:
    lines: list[str] = []
    try:
        with Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as redis:
            stream_info = redis.xinfo_stream("taskiq")
            groups = redis.xinfo_groups("taskiq")
            group = next(
                (item for item in groups if item.get("name") == "taskiq"),
                None,
            )
            if group is None:
                lines.append("    redis: taskiq consumer group not found")
                return lines

            lines.append(
                "    redis: "
                f"stream_length={stream_info.get('length', '?')} "
                f"group_pending={group.get('pending', '?')} "
                f"lag={group.get('lag', '?')} "
                f"last_delivered={group.get('last-delivered-id', '?')}",
            )
            pending = redis.execute_command(
                "XPENDING",
                "taskiq",
                "taskiq",
                "-",
                "+",
                100,
            )
            related = 0
            for entry in pending:
                message_id, consumer, idle_ms, deliveries = entry
                entries = redis.xrange("taskiq", message_id, message_id)
                if not entries:
                    continue
                _, fields = entries[0]
                raw_data = fields.get("data")
                if not raw_data:
                    continue
                try:
                    message = json.loads(raw_data)
                except json.JSONDecodeError:
                    continue
                task_args = message.get("args", [])
                if not isinstance(task_args, list):
                    task_args = []
                if not job_ids.intersection({str(value) for value in task_args}):
                    continue
                related += 1
                lines.append(
                    "    redis pending task: "
                    f"id={message_id} consumer={consumer} "
                    f"idle={float(idle_ms) / 1000:.1f}s deliveries={deliveries} "
                    f"name={message.get('task_name')!r} args={task_args!r}",
                )
            if related == 0:
                lines.append("    redis pending task: none matched current job ids")
    except Exception as exc:
        lines.append(f"    redis diagnostics unavailable: {exc}")
    return lines


def _runtime_diagnostics(
    settings: Settings,
    *,
    job_ids: set[str],
) -> str:
    lines = ["  diagnostics:"]

    ffmpeg_processes = _active_ffmpeg_processes()
    if ffmpeg_processes:
        lines.append("    ffmpeg:")
        lines.extend(f"      {process}" for process in ffmpeg_processes)
    else:
        lines.append("    ffmpeg: no active process found")

    outputs = _temporary_media_outputs()
    if outputs:
        lines.append("    temporary media outputs:")
        lines.extend(f"      {output}" for output in outputs[:10])
    else:
        lines.append("    temporary media outputs: none found")

    lines.extend(_redis_queue_diagnostics(settings, job_ids=job_ids))
    return "\n".join(lines)


async def ensure_media_processing_job(episode_id: UUID) -> None:
    settings = Settings()
    database = create_database(settings.database_url)
    enqueue_job_id: UUID | None = None

    try:
        async with database.session_factory() as session:
            download_job = await DownloadJobService(session).get_latest_job(episode_id)
            if download_job is None:
                raise SmokeTestError(
                    "Episode has no download job. "
                    "storage-media-smoke does not start torrent downloads.",
                )
            if download_job.job_status is not DownloadJobStatus.COMPLETED:
                raise SmokeTestError(
                    "Episode download is not completed: "
                    f"{download_job.job_status.value}",
                )

            service = MediaProcessingJobService(session)
            job = await service.get_latest_job(episode_id)
            if job is None:
                job = await service.create_for_download_job(download_job.id)
                enqueue_job_id = job.id
            elif job.job_status is MediaProcessingJobStatus.FAILED:
                job = await service.retry_job(job.id)
                enqueue_job_id = job.id

        if enqueue_job_id is not None:
            await process_media_job.kiq(str(enqueue_job_id))
            print(f"  media processing job enqueued: {enqueue_job_id}", flush=True)
        else:
            print("  media processing: existing job is running or completed", flush=True)
    finally:
        await database.dispose()


async def ensure_media_preparation_job(episode_id: UUID) -> None:
    settings = Settings()
    database = create_database(settings.database_url)
    enqueue_job_id: UUID | None = None

    try:
        async with database.session_factory() as session:
            asset = await MediaAssetService(session).get_for_episode(episode_id)
            if asset is None or asset.metadata_updated_at is None:
                raise SmokeTestError(
                    "Episode has no materialized MediaAsset metadata yet.",
                )

            variant = await MediaVariantService(session).get_playable_variant(asset.id)
            playable_current = (
                variant is not None
                and variant.is_current(
                    source_path=asset.path,
                    source_metadata_updated_at=asset.metadata_updated_at,
                )
            )
            needs_preparation = not playable_current or not asset.thumbnail_ready
            if not needs_preparation:
                print("  media preparation: playable and thumbnail are ready", flush=True)
                return

            service = MediaPreparationJobService(session)
            job = await service.get_latest_job(asset.id)
            if job is not None and job.job_status in {
                MediaPreparationJobStatus.PENDING,
                MediaPreparationJobStatus.PROCESSING,
            }:
                print(
                    f"  media preparation: existing job is {job.job_status.value}: {job.id}",
                    flush=True,
                )
                return

            if job is None or job.job_status in {
                MediaPreparationJobStatus.FAILED,
                MediaPreparationJobStatus.COMPLETED,
            }:
                job = await service.create_job(
                    media_asset_id=asset.id,
                    source_path=asset.path,
                    source_metadata_updated_at=asset.metadata_updated_at,
                    thumbnail_ready=asset.thumbnail_ready,
                )
                if job is not None:
                    enqueue_job_id = job.id
            elif job.job_status is MediaPreparationJobStatus.PENDING:
                enqueue_job_id = job.id

        if enqueue_job_id is not None:
            await process_media_preparation.kiq(str(enqueue_job_id))
            print(f"  media preparation job enqueued: {enqueue_job_id}", flush=True)
        else:
            print("  media preparation: no new job required", flush=True)
    finally:
        await database.dispose()


async def ensure_media_asset_processing(
    *,
    api_url: str,
    episode_id: UUID,
) -> None:
    payload = http_get(
        api_url,
        f"/api/episodes/{episode_id}/media",
    )
    if not isinstance(payload, dict):
        raise SmokeTestError("Episode does not have a materialized MediaAsset")

    asset_id = payload.get("id")
    if not isinstance(asset_id, str):
        raise SmokeTestError("MediaAsset response has no id")

    subtitle_tracks = payload.get("subtitle_tracks")
    attachments = payload.get("attachments")
    if not isinstance(subtitle_tracks, list) or not isinstance(attachments, list):
        raise SmokeTestError("MediaAsset response has invalid processing collections")

    enqueue_subtitles = payload.get("subtitle_tracks_processed_at") is None and not any(
        isinstance(track, dict) and track.get("status") == "processing"
        for track in subtitle_tracks
    )
    enqueue_attachments = payload.get("attachments_processed_at") is None and not any(
        isinstance(attachment, dict) and attachment.get("status") == "processing"
        for attachment in attachments
    )

    if enqueue_subtitles:
        await process_subtitle_tracks.kiq(asset_id)
        print(f"  subtitle processing task enqueued: asset={asset_id}", flush=True)

    if enqueue_attachments:
        await process_media_attachments.kiq(asset_id)
        print(f"  attachment processing task enqueued: asset={asset_id}", flush=True)


def wait_for_media_processing(
    *,
    api_url: str,
    episode_id: UUID,
    timeout_seconds: float,
) -> dict[str, object]:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started_at = time.monotonic()
    deadline = started_at + timeout_seconds
    last_status: tuple[object, ...] | None = None

    while time.monotonic() < deadline:
        payload = _require_object(
            http_get(
                api_url,
                f"/api/episodes/{episode_id}/media-processing-jobs/latest",
            ),
            "media-processing-jobs/latest",
        )
        signature = (
            payload.get("status"),
            payload.get("attempt_count"),
            payload.get("error_message"),
        )
        if signature != last_status:
            print(
                "  media processing: "
                f"status={payload.get('status')} "
                f"attempts={payload.get('attempt_count', 0)}",
                flush=True,
            )
            last_status = signature

        status = payload.get("status")
        if status == "completed":
            return payload
        if status == "failed":
            raise SmokeTestError(
                "Media processing failed: "
                f"{payload.get('error_message') or 'unknown error'}",
            )

        time.sleep(2)

    raise SmokeTestError(
        "Timed out waiting for media processing after "
        f"{time.monotonic() - started_at:.1f}s",
    )


def wait_for_media_asset_processing(
    *,
    api_url: str,
    episode_id: UUID,
    timeout_seconds: float,
) -> dict[str, object]:
    started_at = time.monotonic()
    deadline = started_at + timeout_seconds
    last_signature: tuple[object, ...] | None = None

    while time.monotonic() < deadline:
        payload = http_get(
            api_url,
            f"/api/episodes/{episode_id}/media",
        )
        if not isinstance(payload, dict):
            raise SmokeTestError("Episode does not have a materialized MediaAsset")

        subtitle_tracks = payload.get("subtitle_tracks")
        attachments = payload.get("attachments")
        if not isinstance(subtitle_tracks, list) or not isinstance(attachments, list):
            raise SmokeTestError("MediaAsset response has invalid processing collections")

        signature = (
            payload.get("thumbnail_status"),
            payload.get("subtitle_tracks_processed_at"),
            tuple(
                track.get("status")
                for track in subtitle_tracks
                if isinstance(track, dict)
            ),
            payload.get("attachments_processed_at"),
            tuple(
                attachment.get("status")
                for attachment in attachments
                if isinstance(attachment, dict)
            ),
        )
        if signature != last_signature:
            print(
                "  derived artifacts: "
                f"thumbnail={payload.get('thumbnail_status')} "
                f"subtitles={payload.get('subtitle_tracks_processed_at') is not None} "
                f"attachments={payload.get('attachments_processed_at') is not None}",
                flush=True,
            )
            last_signature = signature

        if payload.get("thumbnail_status") == "failed":
            raise SmokeTestError(
                "Thumbnail processing failed: "
                f"{payload.get('thumbnail_error_message') or 'unknown error'}",
            )

        failed_subtitles = [
            track
            for track in subtitle_tracks
            if isinstance(track, dict) and track.get("status") == "failed"
        ]
        if failed_subtitles:
            raise SmokeTestError(
                "Subtitle processing failed: "
                f"{failed_subtitles[0].get('error_message') or 'unknown error'}",
            )

        failed_attachments = [
            attachment
            for attachment in attachments
            if isinstance(attachment, dict) and attachment.get("status") == "failed"
        ]
        if failed_attachments:
            raise SmokeTestError(
                "Attachment processing failed: "
                f"{failed_attachments[0].get('error_message') or 'unknown error'}",
            )

        thumbnail_ready = (
            payload.get("thumbnail_status") == "completed"
            and payload.get("thumbnail_sprite_path")
            and payload.get("thumbnail_vtt_path")
        )
        subtitles_ready = payload.get("subtitle_tracks_processed_at") is not None
        attachments_ready = payload.get("attachments_processed_at") is not None
        if thumbnail_ready and subtitles_ready and attachments_ready:
            return payload

        time.sleep(2)

    raise SmokeTestError(
        "Timed out waiting for derived media artifacts after "
        f"{time.monotonic() - started_at:.1f}s",
    )


def wait_for_playable(
    *,
    api_url: str,
    episode_id: UUID,
    settings: Settings,
    timeout_seconds: float,
) -> dict[str, object]:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started_at = time.monotonic()
    deadline = started_at + timeout_seconds
    last_signature: tuple[object, ...] | None = None
    last_activity_report = started_at - 30.0
    processing: object = None
    preparation: dict[str, object] | None = None
    playable: dict[str, object] | None = None

    while time.monotonic() < deadline:
        processing = http_get(
            api_url,
            f"/api/episodes/{episode_id}/media-processing-jobs/latest",
        )
        preparation = _validate_preparation_payload(
            http_get(
                api_url,
                f"/api/episodes/{episode_id}/media-preparation-jobs/latest",
            ),
        )
        playable_payload = http_get(
            api_url,
            f"/api/episodes/{episode_id}/playable-media",
        )
        playable = (
            _require_object(playable_payload, "playable-media")
            if playable_payload is not None
            else None
        )

        signature = (
            processing.get("status") if isinstance(processing, dict) else None,
            processing.get("attempt_count") if isinstance(processing, dict) else None,
            processing.get("error_message") if isinstance(processing, dict) else None,
            preparation.get("status") if preparation is not None else None,
            preparation.get("attempt_count") if preparation is not None else None,
            preparation.get("operation") if preparation is not None else None,
            preparation.get("error_message") if preparation is not None else None,
            playable.get("status") if playable is not None else None,
            playable.get("current") if playable is not None else None,
            playable.get("error_message") if playable is not None else None,
        )
        if signature != last_signature:
            print(
                _state_summary(
                    processing=processing if isinstance(processing, dict) else None,
                    preparation=preparation,
                    playable=playable,
                ),
            )
            last_signature = signature

        if isinstance(processing, dict) and processing.get("status") == "failed":
            raise SmokeTestError(
                "Media processing job failed: "
                f"{processing.get('error_message') or 'unknown error'}",
            )

        if preparation is not None and preparation.get("status") == "failed":
            raise SmokeTestError(
                "Media preparation job failed: "
                f"{preparation.get('error_message') or 'unknown error'}",
            )

        if playable is not None:
            status = playable.get("status")
            current = playable.get("current")
            path = playable.get("path")
            if status == "failed":
                raise SmokeTestError(
                    "Playable media variant failed: "
                    f"{playable.get('error_message') or 'unknown error'}",
                )
            if status == "completed" and current is True and path:
                return playable

        now = time.monotonic()
        if now - last_activity_report >= 30.0:
            ffmpeg_processes = _active_ffmpeg_processes()
            outputs = _temporary_media_outputs()
            activity = f"  activity: elapsed={now - started_at:.0f}s"
            if ffmpeg_processes:
                activity += f" ffmpeg=running({len(ffmpeg_processes)})"
            else:
                activity += " ffmpeg=none"
            if outputs:
                activity += f" temp_outputs={', '.join(outputs[:3])}"
            print(activity, flush=True)
            last_activity_report = now

        if (
            preparation is not None
            and preparation.get("status") == "completed"
            and (
                playable is None
                or playable.get("status") != "completed"
                or playable.get("current") is not True
            )
        ):
            raise SmokeTestError(
                "Media preparation is completed but playable media is not current. "
                f"preparation={preparation!r}, playable={playable!r}",
            )

        time.sleep(2)

    elapsed_seconds = time.monotonic() - started_at
    job_ids = {
        str(job_id)
        for payload in (processing, preparation)
        if isinstance(payload, dict)
        for job_id in (payload.get("id"),)
        if job_id
    }
    raise SmokeTestError(
        "Timed out waiting for a current playable media variant after "
        f"{elapsed_seconds:.1f}s (limit={timeout_seconds:g}s).\n"
        f"{_state_summary(
            processing=processing if isinstance(processing, dict) else None,
            preparation=preparation,
            playable=playable,
        )}\n"
        f"{_runtime_diagnostics(settings, job_ids=job_ids)}",
    )


def wait_for_streaming_package(
    *,
    api_url: str,
    episode_id: UUID,
    timeout_seconds: float,
) -> dict[str, object]:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started_at = time.monotonic()
    deadline = started_at + timeout_seconds
    last_signature: tuple[object, ...] | None = None
    last_report = started_at - 30.0
    streaming: dict[str, object] | None = None

    while time.monotonic() < deadline:
        payload = http_get(
            api_url,
            f"/api/episodes/{episode_id}/streaming-media",
        )
        if payload is not None:
            streaming = _require_object(payload, "streaming-media")
            signature = (
                streaming.get("status"),
                streaming.get("error_message"),
                streaming.get("hls_master_key"),
                streaming.get("dash_manifest_key"),
                len(streaming.get("representations", []))
                if isinstance(streaming.get("representations"), list)
                else None,
            )
            if signature != last_signature:
                print(
                    "  streaming: "
                    f"status={streaming.get('status')} "
                    f"representations={signature[-1]}",
                    flush=True,
                )
                last_signature = signature

            if streaming.get("status") == "completed":
                return streaming

            if streaming.get("status") == "failed":
                raise SmokeTestError(
                    "Streaming package failed: "
                    f"{streaming.get('error_message') or 'unknown error'}",
                )

        now = time.monotonic()
        if now - last_report >= 30.0:
            print(
                "  activity: "
                f"streaming-package elapsed={now - started_at:.0f}s "
                f"status={streaming.get('status') if streaming else 'pending'}",
                flush=True,
            )
            last_report = now

        time.sleep(2)

    elapsed_seconds = time.monotonic() - started_at
    raise SmokeTestError(
        "Timed out waiting for a completed current streaming package after "
        f"{elapsed_seconds:.1f}s (limit={timeout_seconds:g}s)",
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
            "Ensure an episode's downstream media pipeline is runnable, then "
            "verify derived artifacts through the configured storage backend."
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
        help="Wait time per pipeline stage",
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

    await ensure_media_processing_job(args.episode_id)
    wait_for_media_processing(
        api_url=args.api_url,
        episode_id=args.episode_id,
        timeout_seconds=args.timeout,
    )

    await ensure_media_preparation_job(args.episode_id)
    await ensure_media_asset_processing(
        api_url=args.api_url,
        episode_id=args.episode_id,
    )
    playable = wait_for_playable(
        api_url=args.api_url,
        episode_id=args.episode_id,
        settings=settings,
        timeout_seconds=args.timeout,
    )

    await ensure_media_preparation_job(args.episode_id)
    media = wait_for_media_asset_processing(
        api_url=args.api_url,
        episode_id=args.episode_id,
        timeout_seconds=args.timeout,
    )

    variant_key = playable.get("path")
    if not isinstance(variant_key, str) or not variant_key:
        raise SmokeTestError("Playable media has no storage object key")

    streaming = await _ensure_and_wait_for_streaming_package(
        episode_id=args.episode_id,
        api_url=args.api_url,
        timeout_seconds=args.timeout,
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


async def _ensure_and_wait_for_streaming_package(
    *,
    episode_id: UUID,
    api_url: str,
    timeout_seconds: float,
) -> dict[str, object]:
    settings = Settings()
    database = create_database(settings.database_url)
    enqueue_job_id: UUID | None = None

    try:
        async with database.session_factory() as session:
            asset = await MediaAssetService(session).get_for_episode(episode_id)
            if asset is None:
                raise SmokeTestError("Episode does not have a materialized MediaAsset")

            variant = await MediaVariantService(session).get_playable_variant(asset.id)
            if variant is None or not variant.ready or variant.path is None:
                raise SmokeTestError("Episode has no ready playable media variant")

            service = MediaStreamingPackageService(session)
            package = await service.get_for_variant(variant.id)
            current = (
                package is not None
                and package.is_current(
                    source_path=variant.path,
                    source_variant_updated_at=variant.updated_at,
                )
            )
            if current:
                print("  media packaging: current package already exists", flush=True)
            else:
                active = await service.get_active_job(variant.id)
                if active is not None:
                    if active.status == MediaPackagingJobStatus.PENDING.value:
                        enqueue_job_id = active.id
                    else:
                        print(
                            f"  media packaging: already processing job={active.id}",
                            flush=True,
                        )
                else:
                    job = await service.create_job(media_variant_id=variant.id)
                    if job is not None:
                        enqueue_job_id = job.id

        if enqueue_job_id is not None:
            await process_media_packaging.kiq(str(enqueue_job_id))
            print(f"  media packaging job enqueued: {enqueue_job_id}", flush=True)
    finally:
        await database.dispose()

    return wait_for_streaming_package(
        api_url=api_url,
        episode_id=episode_id,
        timeout_seconds=timeout_seconds,
    )




if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except SmokeTestError as exc:
        print(f"[storage-media-smoke] FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
