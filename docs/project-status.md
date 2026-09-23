# Project Status

## Current Phase

Episode download workflow execution is now in progress. The torrent infrastructure layer is complete; the current work adds Taskiq execution and persistent download orchestration.

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
- Shared `/data/downloads` between worker and qBittorrent
- Added deterministic adapter tests and CI runtime checks

## Current Workflow

```
Browser
  → Nyaa search
  → select release
  → create Anime + Episodes
  → PostgreSQL
  → create persistent DownloadJob
  → enqueue Taskiq task
  → worker
  → TorrentClient / qBittorrent
  → persist DownloadJob progress/state
```

## Current PR — Episode Download Execution

The current PR implements the execution layer for GitHub Issue #4:

- `POST /api/episodes/{episode_id}/download-jobs` creates an active persistent job and enqueues Taskiq work
- the API owns only task dispatch; the worker owns download execution
- worker execution is isolated in a `DownloadRunner` application service
- retries/restarts reuse the per-job qBittorrent tag instead of blindly adding duplicate torrents
- qBittorrent progress is persisted back to PostgreSQL
- completed, failed, and terminal jobs remain observable through the existing job status API
- deterministic API/runner tests cover enqueueing, duplicate-job behavior, success, resume, and failure paths

Actual live torrent downloads are intentionally not part of normal CI; integration tests continue to use deterministic external-service boundaries.

### Next Phase

After this PR, the frontend should get a separate Anime Detail / Episode Management UI:

- Anime detail/edit/delete
- Episode list and metadata
- per-episode download action
- persistent job status/progress display

## Out of Scope for This Phase

Do not expand the first download-workflow change into the later media pipeline stages:

- media inspection
- subtitle normalization
- transcoding
- HLS/DASH packaging
- SeaweedFS upload

These should remain separate follow-up phases.

## Handoff Notes

For a new development session, use this document together with `AGENTS.md`, the relevant architecture and decision documents, the current open pull request, and recent commits. Treat the repository state as authoritative and update this file when the project phase changes.
