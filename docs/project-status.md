# Project Status

## Current Phase

Anime and Episode persistence and management are complete. The next development phase is the Episode download workflow.

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

## Current Workflow

```
Browser
  → Nyaa search
  → select release
  → create Anime + Episodes
  → PostgreSQL
```

Actual torrent downloading and media conversion are not implemented yet.

## Next Phase

### Episode Download Workflow

Tracked by GitHub Issue #4: `feat: implement Episode download workflow`.

The intended first stage is:

```
Episode
  → create persistent download job
  → enqueue Taskiq work
  → torrent-client adapter/service
  → download
  → persist download/job state
```

The implementation should keep PostgreSQL as the source of truth for persistent state and keep external infrastructure behind explicit adapters/services.

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
