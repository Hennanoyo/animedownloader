# Project Status

## Current Phase

The project is in the frontend Anime Detail / Episode Management phase. PR #12 is implementing Anime edit/delete.

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

CI passed for PR #8 with Backend, Frontend, and Integration checks.

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
```

## Current Phase — Frontend Anime Detail / Episode Management

PR #12 focuses on Anime edit/delete.

### PR #12 Scope

- Add an Anime edit UI from the detail page
- Reuse the existing Anime update API
- Validate edit fields with TanStack Form + Zod
- Invalidate/update Anime detail and list query caches after a successful edit
- Add Anime delete with explicit confirmation
- Navigate back to the Anime catalog after deletion
- Keep Episode editing and download-job UI out of scope

### Planned Follow-up

PR #13 will add the per-Episode DownloadJob UI and persistent progress display.

The frontend should remain separate from the backend execution implementation so API/worker behavior can continue to be tested independently.

## Out of Scope for This Phase

Do not expand the first download workflow into later media pipeline stages:

- media inspection
- subtitle normalization
- transcoding
- HLS/DASH packaging
- SeaweedFS upload

These should remain separate follow-up phases.

## Handoff Notes

For a new development session, use this document together with `AGENTS.md`, the relevant architecture and decision documents, the current open pull request, and recent commits. Treat the repository state as authoritative and update this file when the project phase changes.
