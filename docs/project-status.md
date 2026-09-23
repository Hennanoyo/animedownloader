# Project Status

## Current Phase

The project has completed Anime/Episode management, persistent torrent download execution, download controls, and media inspection infrastructure. The current slice establishes persistent post-download media processing and FFprobe inspection.

## Completed

### PR #3 — Anime and Episode Management

Merged into `main` as commit `9a48d0c1f85b40541712275220a14eecab811a0e`.

- Persistent `Anime` and `Episode` models with PostgreSQL and Alembic
- Anime and Episode CRUD API
- Episode Nyaa provenance and torrent metadata persistence
- Episode download/conversion status fields for future processing
- Anime creation UI
- Per-episode Nyaa release selection and title cleanup
- Anime catalog page
- PostgreSQL CRUD and cascade integration coverage in CI

### PR #6 — Persistent Download Jobs

Merged into `main` as commit `734366149c0779129f00d7ae0ea19ce3cd8460f9`.

- Added the `animedownloader-download` domain
- Added persistent `DownloadJob` state in PostgreSQL
- Enforced one active (`pending` / `downloading`) job per Episode at the database level
- Added explicit download-job state transitions and terminal history
- Added `GET /api/download-jobs/{job_id}`
- Added the `download_jobs` Alembic migration
- Added deterministic state/API tests and PostgreSQL migration coverage in CI

### PR #7 — Torrent Infrastructure

Merged into `main` as commit `767ad92ce7f88f0266e2845a3d4a9833522ec80b`.

- Added the domain-neutral `TorrentClient` protocol and torrent models
- Added the qBittorrent Web API adapter
- Added job-tag correlation for torrents
- Added qBittorrent configuration and Compose service
- Shared `/downloads` between worker and qBittorrent
- Added deterministic adapter tests and CI runtime checks

### PR #8 — Episode Download Execution

Merged into `main` as commit `a8610bb1cb39c508b64e9d9111b67b39412fc32f`.

- Added `POST /api/episodes/{episode_id}/download-jobs`
- Added Taskiq dispatch through Redis
- Added Worker-side `DownloadRunner` orchestration
- Reused qBittorrent torrents by per-job tag across worker restarts/retries
- Persisted qBittorrent progress and terminal state to PostgreSQL
- Added duplicate active-job handling
- Added deterministic API/runner coverage
- Added Worker runtime verification to CI

### PR #9 — qBittorrent Pending Add Handling

Merged into `main`.

- Accepted qBittorrent v5.2 pending torrent-add responses
- Added adapter coverage for pending and mixed add-response payloads

### PR #10 — qBittorrent Environment and Download Path Fixes

Merged into `main` as commit `ce2a9f4d646c70d684603949f23fcccb6fcc302d`.

- Loaded `QBITTORRENT_API_KEY` from `server/.env` through Pydantic Settings
- Aligned the shared download volume to `/downloads` for API/Worker/qBittorrent
- Let qBittorrent create and own per-job download directories
- Removed completed torrents after successful download without deleting downloaded files
- Allowed both `localhost:5173` and `127.0.0.1:5173` CORS origins
- Restored Nyaa client lifecycle management in the release-search dependency
- Updated development, devcontainer, and CI configuration for the new path/origins

### PR #11 — Anime Detail and Episode List

Merged into `main`.

- Added `/animes/:animeId` detail route
- Added read-only Anime detail view with schedule metadata
- Added Episode list with source, torrent metadata, and processing statuses
- Linked Anime catalog entries to their detail pages
- Added focused single-Anime API coverage
- Kept edit/delete and download mutations out of scope for this slice

### PR #12 — Anime Edit and Delete

Merged into `main`.

- Added Anime metadata editing with TanStack Form + Zod
- Kept Episode data unchanged during Anime edits
- Updated Anime detail and catalog caches after successful edits
- Added explicit Anime deletion confirmation
- Returned to the Anime catalog after successful deletion
- Added API and validation coverage
- Added repository guidance to use `just` as the canonical local validation entry point

### PR #13 — Episode Download UI

Merged into `main` as commit `d057a4d7c14a36caff36a25779af87abec5951b4`.

- Added a frontend DownloadJob entity and typed API client
- Added an Episode Download action to Anime detail
- Showed queued/downloading progress with automatic polling
- Restored the latest persisted Job after page refresh
- Added completed, failed, and cancelled states with retry/redownload actions
- Added the Episode latest DownloadJob API endpoint
- Added API and frontend response coverage

### PR #14 — Media Inspection Infrastructure

Merged into `main` as commit `19ae042137a5dffd2b54fd4a16a7a1433521822f`.

- Added the `animedownloader-media` technical library
- Added async FFprobe execution without a shell
- Added typed parsing for format, stream, attachment, and chapter metadata
- Added deterministic inspector tests with a fake process runner
- Registered the media package in the backend image and uv workspace

### PR #15 — Episode Management and Release Reuse

Merged into `main` as commit `1adf634e60d66900426a5fe0e9e934b879c626a2`.

- Added Episode add/edit/delete operations from Anime detail
- Reused the existing Nyaa release picker for Episode creation
- Added Episode CRUD API and frontend mutations
- Updated frontend query caches after Episode mutations
- Added API and frontend coverage

### PR #16 — Download Job Controls

Merged into `main` as commit `9773b092a72856dff3907079d74f2da5259beb65`.

- Added persistent `paused` DownloadJob status
- Added qBittorrent pause/resume controls behind `TorrentClient`
- Added active-job cancel with partial torrent-data removal
- Added terminal DownloadJob record deletion while retaining completed media files
- Kept paused jobs active and unique per Episode
- Reconciled worker behavior with pause/cancel state changes
- Added API, worker, torrent adapter, and frontend coverage

## Current Workflow

```
Browser
  → Nyaa search
  → select release
  → create Anime + Episodes
  → PostgreSQL
  → Anime detail
  → edit/delete Anime or Episode
  → create persistent DownloadJob
  → enqueue Taskiq task
  → worker
  → TorrentClient / qBittorrent
  → persist DownloadJob progress/state
  → Browser polls and controls DownloadJob
```

## Current Phase — Media Processing Job

PR #17 establishes the first post-download processing stage.

### PR #17 Scope

- Add persistent `MediaProcessingJob` state and transitions
- Create a processing job after `DownloadJob.COMPLETED`
- Run FFprobe inspection through the existing `animedownloader-media` library
- Persist the media path and structured probe metadata
- Expose processing status and latest Episode processing state through the API
- Retry failed inspection without re-downloading
- Keep processing state independent from terminal DownloadJob state

### Processing Rules

- DownloadJob remains the source of truth for torrent acquisition state
- MediaProcessingJob owns post-download processing state
- FFprobe inspection is the first processing step
- Failed inspection is retryable without re-downloading the torrent
- DownloadJob remains COMPLETED when media processing fails
- Deleting a DownloadJob does not delete MediaProcessingJob history

### Explicitly Out of Scope

- Subtitle normalization
- Transcoding or remuxing
- HLS/DASH packaging
- SeaweedFS upload
- Player/playback UI
- Media file deletion or retention policy changes

## Planned Follow-up

After PR #17:

- subtitle normalization
- transcoding/remuxing
- HLS/DASH packaging
- SeaweedFS upload
- player and playback tooling

## Handoff Notes

For a new development session, use this document together with `AGENTS.md`, the relevant architecture and decision documents, the current open pull request, and recent commits. Treat the repository state as authoritative and update this file when the project phase changes.
