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

## Media Hardware Acceleration

- Treat `FFMPEG_VIDEO_ENCODER=auto` as the default development/runtime behavior.
- When `auto` is selected, probe real `hevc_nvenc` encoding capability before a transcode and fall back to `libx265` when NVIDIA GPU access, drivers, or NVENC are unavailable.
- Do not require GPU-specific commands or settings for the media pipeline to function.
- Keep CUDA hardware-frame decoding out of the shared playable/thumbnail preparation path unless the filter graph has explicit, tested hardware-frame compatibility.
- GPU-specific Compose configuration may be used internally to expose an available NVIDIA device, but application-level encoder selection must remain portable.

## Media Source Recovery Rules

- Treat a completed DownloadJob as download execution/history; physical source media remains local filesystem data under the configured download root.
- Reuse the shared media-source resolver so missing, empty, found, and ambiguous source states have one deterministic contract.
- Never automatically re-download a missing source or automatically delete a source directory.
- User-selected media source paths must be relative to the DownloadJob directory and validated against path traversal.
- Orphan source cleanup must check both DownloadJob and MediaProcessingJob references before allowing deletion.
- Deleting a source directory must never implicitly delete derived media-storage artifacts or persistent processing history.

## Release Provenance & Replacement Rules

- An Episode may persist a nullable reference to an existing enabled ReleaseGroup; release discovery/ingestion must never auto-create ReleaseGroup records.
- Treat the Episode's release provenance as durable metadata separate from the ephemeral provider search result.
- Re-ingestion of the same release may refresh mutable provider metadata and a known ReleaseGroup reference, but must not overwrite user-edited Episode title or execution state.
- Release replacement must be an explicit user action. Never replace an Episode automatically because another release appears newer, healthier, or better seeded.
- Reject release replacement when the Episode has any DownloadJob, MediaProcessingJob, or MediaAsset history. Preserving existing execution/media history is safer than rewriting provenance around it.
- A successful replacement updates release provenance/metadata only; it must not create or start a DownloadJob.
- Unknown release groups remain unlinked until an operator creates/configures the corresponding ReleaseGroup.

## Anime Release Preferences & Ranking Rules

- The persisted Anime Release Preference record is a compatibility projection of the canonical Discovery Search Plan, not a separate user-facing configuration surface.
- Search Plan group/resolution/video-codec/source values may be projected into the legacy preference record so existing ranking and older API clients remain compatible.
- Ranking must remain deterministic and explainable through explicit match reasons.
- A Search Plan field that is not configured must not penalize or exclude a release.
- Ranking must not silently start downloads, replace Episodes, or mutate persistent Episode release provenance.
- Current provider metadata such as seeders may only be used as a deterministic tie-breaker after explicit ranking criteria; it must not override an explicit configured match.
- The user-facing automation thresholds and mode belong to Discovery configuration and must be evaluated there.

## Release Discovery Candidate Inbox Rules

- Raw Nyaa RSS/search payloads remain ephemeral. Persist only normalized discovery-candidate records needed for review, deduplication, and later acceptance.
- A persisted candidate is not an Episode and is not authoritative release state. It may be updated with the latest observed provider metadata without creating or replacing an Episode.
- Candidate identity is stable per Anime/provider/source ID so repeated discovery runs update an existing candidate instead of creating duplicates.
- Persist ranking score and explicit ranking reasons from the discovery observation; changing the saved Discovery Search Plan must not silently rewrite unrelated historical candidate records until a later discovery observes the release again.
- Keep discovery-run history separate from DownloadJob, MediaProcessingJob, and Episode execution state.
- Periodic scheduling is DB-driven and restart-safe. Use transactional row locking/claiming so multiple API instances do not enqueue the same due schedule concurrently.
- Candidate collection must never create an Episode, replace an Episode, create a DownloadJob, or start a torrent automatically.
- Candidate review may mark a candidate reviewed/rejected/stale; explicit acceptance must revalidate the persisted candidate against the current Anime and reuse Episode ingestion/replacement guards.
- Rejected and stale candidates must not be accepted. Re-accepting an already accepted candidate must remain idempotent when the underlying release is unchanged.
- If acceptance finds an existing Episode for the same Anime/episode number with a different release, return a replacement candidate and require a separate explicit replacement action.
- Explicit replacement must identify the target Episode and must verify the target belongs to the candidate Anime and has the same episode number before using the existing replacement-history guards.
- Candidate acceptance and replacement must never create or start a DownloadJob implicitly; downloading remains a separate explicit action.
- Keep candidate lists bounded at the API boundary and make destructive candidate cleanup explicit; never run cleanup implicitly as part of discovery.
- Discovery Search Plans are bounded and deterministic. Never introduce Cartesian-product query expansion or hidden progressive broadening/retry.
- Persist per-query discovery diagnostics when a Search Plan executes multiple provider queries, but never persist raw Nyaa/RSS payloads merely for diagnostics.
- Treat provider result-limit detection as a diagnostic signal rather than proof of truncation; expose the signal so operators can refine search plans.
- Automatic candidate handling is configured as part of the Anime Discovery configuration and defaults to off.
- Automatic selection may use only actionable, uniquely matched candidates and must re-evaluate the current Discovery configuration immediately before Episode ingestion.
- When Search Plan criteria matching is required, all configured criteria used as selection guards must match; automation must not silently broaden into unrestricted downloads.
- Automatic selection must preserve deterministic ranking and expose decision reasons in Discovery results/activity; a dedicated dry-run panel is not required.
- Candidate automation uses persistent claim state with transactional row locking and restart-safe stale-claim recovery.
- Automatic acceptance may not perform Episode replacement. A replacement candidate remains blocked for automation and requires the existing explicit replacement workflow.
- Automatic download creation must use the existing DownloadJobService, never create duplicate active jobs, and must not automatically retry failed/cancelled terminal history.
- Candidate automation may enqueue an existing pending DownloadJob after a restart, but it must never start a paused download that the user has intentionally paused.
- Search Plan editing, Discovery schedule, and candidate-automation mode are one user-facing Discovery workflow. Do not reintroduce separate Anime preference or automatic-download configuration panels unless a new architecture decision explicitly requires them.

## Storage Rules

- Persist storage `object_key` values in PostgreSQL rather than environment-specific public URLs.
- Treat `source_path`, `object_key`, and public URL as different representations with different responsibilities.
- Use UUID7-backed artifact identity for normal derived artifacts; do not use processing job IDs as durable artifact filenames.
- Use content-addressed SHA-256 identity for reusable resources such as fonts.
- Keep original filenames as metadata rather than embedding them in canonical object keys.
- Define and reuse canonical object keys from `animedownloader_storage.artifacts` instead of duplicating key-format strings in workers or API code.
- Internal and public storage endpoints must be configurable through environment-backed settings.
- Keep SeaweedFS access behind a storage abstraction.

See `docs/architecture/storage.md`.

## Release Profile Operations

- Release parser profiles are versioned per release group and follow the lifecycle draft → active → retired.
- Active profiles are immutable; edits happen by creating a new draft version.
- Representative release-title samples are persistent operational data used for validation and manual regression review.
- Parser health is an aggregate observation signal. Persist only the minimum non-parsed observation data needed for investigation; do not cache raw RSS solely for health.
- Drift signals are advisory. Never auto-edit parser rules, auto-activate profiles, or auto-start downloads because drift was detected.
- A profile created from an observed failure must still pass multi-sample validation and explicit activation.
- Discovery search values may use persisted Release Group suggestions, while the current request remains editable and transient.

## Testing Rules

- Prefer deterministic fixtures and fakes/mocks for external services in unit tests.
- Do not use live Nyaa searches or real torrent downloads in normal CI tests.
- Use small deterministic media fixtures for ffmpeg/media tests.
- Test the narrowest relevant scope first, then run required repository checks.
- Do not weaken or delete a test merely to hide an implementation failure.

A change is complete only after relevant local checks and applicable GitHub Actions checks pass.

### Visual UI Validation

For frontend changes that affect layout, spacing, sizing, responsive behavior, or visual hierarchy, use browser-rendered screenshots when code inspection alone cannot reliably validate the result.

- Prefer the existing Playwright Browser workflow and deterministic API/media mocks so screenshots are stable and do not require live services or real media.
- Capture the relevant desktop and responsive viewports with `page.screenshot({ fullPage: true })` into Playwright's test output directory rather than writing screenshots into the repository.
- Upload the screenshots as temporary workflow artifacts when a visual review is needed, then inspect the rendered result before making further layout changes.
- Treat visual-audit screenshots as temporary evidence. Do not commit generated image files; remove temporary screenshot-only test code after the audit unless the test provides lasting regression value.
- Keep durable browser tests focused on behavior and accessibility. Use Playwright snapshot assertions only when a lasting visual regression test is intentionally warranted.
- When an existing UI change is difficult to judge from source alone, do not assume the layout is correct merely because lint/typecheck/tests pass; use an actual rendered screenshot.

### Runtime Smoke Tests

Runtime smoke tests are developer-facing end-to-end checks for workflows that cross multiple real services or processes. They complement unit/integration tests rather than replacing them.

An agent should consider creating or updating a runtime smoke test when a change:

- crosses multiple runtime boundaries such as API → database → Taskiq/worker → ffmpeg → filesystem/storage;
- depends on real infrastructure wiring such as PostgreSQL, Redis, qBittorrent, SeaweedFS, ffmpeg, or container networking;
- changes a critical user-visible workflow whose failure could be caused by deployment/configuration rather than isolated business logic;
- exposes a workflow that is difficult to validate convincingly with deterministic integration tests alone.

Do not create a runtime smoke test for every small domain or utility change. Prefer the smallest number of workflow-oriented smoke tests that provide meaningful coverage.

Store runtime smoke scripts under `scripts/smoke/` when the collection grows beyond a small number of standalone scripts, and expose them through the repository `justfile`. Command-driven, step-by-step execution is acceptable and preferred over adding unnecessary CI complexity. Smoke commands should be safe to rerun where practical, produce actionable failures, and avoid destructive cleanup unless explicitly named and documented as destructive.

Runtime smoke tests normally belong to local/staging validation rather than the default CI suite when they require existing real media, mutable application state, or environment-specific resources. Keep deterministic unit/integration coverage in CI.

When implementing a PR, the agent should decide whether a runtime smoke test adds material value. If it does, create or update one as part of the PR, run it when the actual environment is available, and tell the user which workflow was verified and whether the test is intended for local/staging use or CI. If it does not add meaningful value, do not create one merely for coverage optics.

## Pre-Commit Validation

Use the repository's `justfile` as the **mandatory** entry point for local validation. Do not manually substitute an equivalent command sequence when a corresponding `just` target exists.

The pre-commit/PR validation flow is mandatory:

1. Make the smallest coherent code change.
2. Run the relevant automatic formatter before committing:
   - Backend changes: `just server-format`.
   - Frontend changes: run `just web-format`.
3. Run the complete required check target after formatting:
   - Frontend-only changes: `just web-check`.
   - Backend-only changes: `just server-check`.
   - Changes affecting both workspaces, shared configuration, or repository-level behavior: `just check`.
4. Do not commit, push, or open/update a pull request until the required check target passes.
5. When a check fails, fix the problem, run the automatic formatter again where applicable, and rerun the complete required check target.
6. When a pull request receives a CI failure, reproduce the failing check locally using the relevant `just` target before making further feature changes.
7. After any CI-driven fix, rerun the corresponding local `just` target, commit the fix, and verify that the new commit starts a fresh CI run.

The `check` targets are verification-only: they must not modify source files. Automatic fixes belong in the `format`/workspace-format targets before `check`. Frontend `web-format` uses ESLint automatic fixes; backend `server-format` uses Ruff formatting.

Keep the local validation command aligned with the `justfile` rather than duplicating its individual commands in this document.

In GitHub Actions, run the affected workspace's automatic formatting target before its check target as a defensive validation step. CI formatting only changes the ephemeral runner workspace and must not be treated as a branch update; the PR branch is updated through normal commits.


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
3. Run the required pre-commit `just` validation for every affected workspace, including the automatic formatting step before the final check.
4. Commit and push the change through the normal Git workflow.
5. Inspect GitHub Actions results when available.
6. Fix CI failures rather than ignoring them.
7. Update documentation when architecture or externally visible behavior changes.

When completing a feature or PR, update `docs/project-status.md` when the current phase, completed work, or next planned work changes.
