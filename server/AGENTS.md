# Backend Agent Instructions

## Stack

- Python 3.14+
- uv
- FastAPI
- Taskiq
- SQLAlchemy
- asyncpg
- Alembic
- PostgreSQL
- Redis when required
- ffmpeg / ffprobe
- SeaweedFS

## Package Layout

- `server/apps`: executable services such as API and worker
- `server/domains`: business/domain behavior
- `server/libs`: reusable infrastructure and technical libraries

Keep infrastructure concerns behind explicit interfaces/adapters. Domain code should not directly construct database sessions, Redis clients, SeaweedFS clients, ffmpeg processes, or torrent clients.

## Async Jobs

Use explicit persistent job state for downloads and media processing.

Recommended conceptual stages include:

`PENDING` → `DOWNLOADING` → `DOWNLOADED` → `INSPECTING` → `TRANSCODING` → `PACKAGING` → `UPLOADING` → `COMPLETED`

with explicit `FAILED` and `CANCELLED` states.

PostgreSQL is authoritative for persistent state. Redis can carry transient progress/events. Taskiq owns execution.

## Python Quality

- Python 3.14+; do not add an upper Python version pin unless required by a dependency.
- Prefer modern Python typing syntax.
- Use async APIs for I/O-bound application operations.
- Keep Ruff, Pyright, and pytest clean.
- Use dependency injection instead of module-level mutable singletons for application resources.

## Media

- Inspect source media before deciding whether transcoding is required.
- HEVC is the primary target codec.
- Reuse a shared CMAF/fMP4 asset set for HLS and DASH.
- Normalize non-ASS subtitles to JASSUB-compatible ASS.
- Preserve fonts/attachments required by subtitles.

## Database

Alembic migrations must be deterministic and reviewed for destructive operations. Do not silently reset or delete persistent data in normal application code.
