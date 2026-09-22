# Project Status

## Current Phase

Episode download workflow is now in progress. The persistent download-job layer is complete; the next implementation step is the torrent infrastructure layer.

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

## Current Workflow

```
Browser
  → Nyaa search
  → select release
  → create Anime + Episodes
  → PostgreSQL
  → persistent DownloadJob
```

Actual torrent downloading and Taskiq execution are not implemented yet.

## Next Phase

### Episode Download Workflow

Tracked by GitHub Issue #4: `feat: implement Episode download workflow`.

The workflow is being implemented in small stages:

```
Episode
  → create persistent download job
  → enqueue Taskiq work
  → torrent-client adapter/service
  → download
  → persist download/job state
```

#### PR B — Torrent Infrastructure

The next PR should establish the infrastructure boundary without starting real download execution:

- define a small torrent-client protocol/interface used by the domain/application layer
- add a qBittorrent Web API adapter behind that interface
- add qBittorrent configuration and Compose service wiring
- define the shared download staging volume/path contract between worker and qBittorrent
- keep qBittorrent-specific request/response types and API details inside the adapter
- add deterministic adapter/configuration tests without requiring a real qBittorrent server in normal CI

Taskiq job dispatch, actual torrent execution, progress polling, and Episode/job orchestration remain follow-up work.

### Out of Scope for This Phase

Do not expand the first download-workflow change into the later media pipeline stages:

- media inspection
- subtitle normalization
- transcoding
- HLS/DASH packaging
- SeaweedFS upload

These should remain separate follow-up phases.

## Handoff Notes

For a new development session, use this document together with `AGENTS.md`, the relevant architecture/decision documents, the current open PR, and recent commits. Treat the repository state as authoritative and update this file when the project phase changes.
