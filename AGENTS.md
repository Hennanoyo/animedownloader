# Agent Instructions

## Project

`animedownloader` is a pnpm + uv monorepo for an anime downloader and web media streaming application.

Repository layout:

- `web/`: frontend monorepo
- `server/`: backend monorepo
- `docs/`: architecture, development notes, and architecture decision records
- `.github/`: repository automation and CI

Before making architectural changes, read the relevant documentation under `docs/`.

## Tooling

- Use `pnpm` for frontend dependencies and workspace operations.
- Use `uv` for Python dependencies and workspace operations.
- Use `just` for repository-level developer commands.
- Development is performed in WSL2 Ubuntu with VSCode Dev Containers and Docker Compose.
- Do not introduce another package manager or task runner without an explicit architectural decision.

## Repository Architecture

Keep these boundaries intact:

- `apps/`: executable applications
- `domains/`: business rules and application/domain behavior
- `libs/`: reusable technical or infrastructure libraries

Backend business logic must not be coupled to frontend code.

Long-running operations must have explicit job state. PostgreSQL is the source of truth for persistent job/media state; Redis is for transient messaging/events when required; Taskiq executes asynchronous jobs.

Infrastructure such as torrent clients, ffmpeg, SeaweedFS, PostgreSQL, and Redis must be accessed through explicit adapters/services rather than being hard-coded throughout domain code.

## Media Rules

- HEVC is the project's primary video codec.
- Avoid unnecessary re-encoding. If the source already satisfies the project's HEVC requirements, prefer remux/package operations where possible.
- HLS and DASH should reuse the same underlying CMAF/fMP4 media assets whenever possible.
- Do not encode the same video twice solely to produce separate HLS and DASH manifests.
- Subtitles that are not directly suitable for JASSUB should be normalized to an ASS representation.
- Preserve required MKV subtitle attachments, especially fonts needed for ASS rendering.
- Thumbnail sprite generation is part of the media packaging pipeline.

See `docs/architecture/media-pipeline.md` and `docs/decisions/`.

## Storage Rules

- Persist storage `object_key` values in PostgreSQL rather than environment-specific public URLs.
- Internal and public storage endpoints must be configurable through environment-backed settings.
- Keep SeaweedFS access behind a storage abstraction.

See `docs/architecture/storage.md`.

## Testing Rules

- Prefer deterministic fixtures and fakes/mocks for external services in unit tests.
- Do not use live Nyaa searches or real torrent downloads in normal CI tests.
- Use small deterministic media fixtures for ffmpeg/media tests.
- Test the narrowest relevant scope first, then run required repository checks.
- Do not weaken or delete a test merely to hide an implementation failure.

A change is complete only after relevant local checks and applicable GitHub Actions checks pass.

## Pre-Commit Validation

Use the repository's `justfile` as the canonical entry point for local validation. Do not manually substitute an equivalent command sequence when a corresponding `just` target exists.

Before committing or opening/updating a pull request:

- For frontend-only changes, run `just web-check`.
- For backend-only changes, run `just server-check`.
- For changes affecting both workspaces, shared configuration, or repository-level behavior, run `just check`.

These targets currently run the same lint, formatting, type-check, and test checks used by CI. Keep the local validation command aligned with the `justfile` rather than duplicating its individual commands in this document.

### Validation workflow

1. After making code changes, run the narrowest relevant `just` validation target first.
2. If any validation fails, fix the implementation and rerun the failed target.
3. After fixing a failure, rerun the complete required `just` validation target before committing.
4. Never open or update a pull request while a locally reproducible lint, formatting, type-check, or test failure remains.
5. When a pull request receives a CI failure, reproduce the failing check locally using the relevant `just` target before making further feature changes.
6. After any CI-driven fix, rerun the corresponding local `just` target and verify that the new commit starts a fresh CI run.

### Repository-level validation

When changes affect multiple workspaces or shared configuration, run `just check`.

## Git Workflow

- Prefer focused branches and small pull requests.
- Do not mix unrelated refactors with feature work.
- Do not commit secrets, credentials, `.env` files, downloaded media, or runtime data.
- Treat destructive database migrations as high-risk changes requiring careful review.

## Working Method

When starting a task:

1. Read `docs/project-status.md` when it exists.
2. Read the relevant architecture and decision documents under `docs/`.
3. Inspect the current branch, relevant open pull request, and recent commits.
4. Verify documented status against the actual code before making changes.

When a task requires code changes:

1. Make the smallest coherent change.
2. Run focused tests/checks.
3. Run the required pre-commit `just` validation for every affected workspace.
4. Commit and push the change through the normal Git workflow.
5. Inspect GitHub Actions results when available.
6. Fix CI failures rather than ignoring them.
7. Update documentation when architecture or externally visible behavior changes.

When completing a feature or PR, update `docs/project-status.md` when the current phase, completed work, or next planned work changes.
