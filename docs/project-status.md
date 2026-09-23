# Project Status

## Current Phase

The project is in the backend media pipeline foundation phase. PR #14 is adding reusable FFprobe-based media inspection infrastructure.

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

## Current Workflow

```
Browser
  → Nyaa search
  → select release
  → create Anime + Episodes
  → PostgreSQL
  → Anime detail
  → edit/delete Anime
  → create persistent DownloadJob
  → enqueue Taskiq task
  → worker
  → TorrentClient / qBittorrent
  → persist DownloadJob progress/state
  → Browser polls persistent DownloadJob state
```

## Current Phase — Backend Media Pipeline Foundations

PR #14 focuses on reusable FFprobe-based media inspection.

### PR #14 Scope

- Add the `animedownloader-media` technical library
- Execute FFprobe asynchronously without a shell
- Parse FFprobe JSON into typed media format, stream, and chapter models
- Preserve stream metadata needed by later subtitle/attachment processing
- Add deterministic unit tests using a fake process runner
- Include the media package and FFmpeg tooling in the backend image
- Do not yet persist a media-processing job or automatically trigger inspection after download
- Do not transcode, remux, package, or upload media in this PR

The inspection layer should remain independent from the Episode/DownloadJob domain so later pipeline orchestration can compose it without coupling the domain to subprocess details.

## Planned Follow-up

After PR #14, continue the media pipeline as separate focused phases:

- persist media-processing job state and trigger inspection after download
- subtitle normalization
- transcoding/remuxing
- HLS/DASH packaging
- SeaweedFS upload
- player and playback tooling

## Handoff Notes

For a new development session, use this document together with `AGENTS.md`, the relevant architecture and decision documents, the current open pull request, and recent commits. Treat the repository state as authoritative and update this file when the project phase changes.
