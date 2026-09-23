# Project Status

## Current Phase

The project has completed Anime/Episode management, persistent torrent download execution, download controls, media inspection infrastructure, and the first persistent post-download media pipeline stages. The current slice records the user-facing metadata of the current MediaAsset before conversion and delivery features are added.

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

## Current Phase — Media Metadata Integration

### PR #17 — Media Processing Jobs

Merged into `main` as commit `57e04d490933aca6dc26871dd69e7ee160b5dce6`.

- Added persistent `MediaProcessingJob` state and transitions
- Created a processing job after `DownloadJob.COMPLETED`
- Ran FFprobe inspection through the existing `animedownloader-media` library
- Persisted the media path and structured probe metadata
- Exposed processing status and latest Episode processing state through the API
- Added retry without re-downloading
- Kept processing state independent from terminal DownloadJob state
- Added a manual trigger for processing an existing completed `DownloadJob`
- Verified Backend, Frontend, and Integration CI successfully

`MediaProcessingJob` remains the execution/history record for post-download processing.

### PR #18 — Media Asset / Episode Integration

Merged into `main` as commit `b3222e675a51e9d2d95faea06b15b2a2794391ef`.

- Added persistent `MediaAsset` with one canonical asset per Episode
- Materialized the successful processing output path into the Episode media asset
- Kept MediaAsset metadata minimal and avoided duplicating the full FFprobe result
- Exposed Episode media information through `GET /api/episodes/{episode_id}/media`
- Kept `DownloadJob` and `MediaProcessingJob` as execution/history records
- Made media asset materialization part of the same transaction as processing completion

The `MediaAsset` record is the current usable media representation for an Episode.

### PR #19 — Media Metadata Integration

In development on `feature/media-metadata`.

Scope:

- Add only the current user-facing media metadata needed by `MediaAsset`
- Materialize selected metadata from the existing typed `MediaProbe`
- Preserve the full probe snapshot only on `MediaProcessingJob` for now
- Track when the current MediaAsset metadata was refreshed
- Re-inspect existing PR #18 assets whose metadata has not yet been materialized
- Extend `GET /api/episodes/{episode_id}/media` with current metadata

Current MediaAsset metadata:

- container format
- duration
- file size
- video codec
- audio codec
- video width and height
- frame rate
- metadata refresh timestamp

Explicitly out of scope:

- Subtitle normalization
- Transcoding or remuxing
- HLS/DASH packaging
- SeaweedFS upload
- Player/playback UI
- Media file deletion or retention policy changes

### Planned Follow-up

After the media metadata slice:

- Subtitle track integration
- Subtitle extraction / normalization
- Chapter, attachment, and sprite integration
- Transcoding/remuxing
- HLS/DASH packaging
- SeaweedFS upload
- Player/playback tooling

## Handoff Notes

For a new development session, use this document together with `AGENTS.md`, the relevant architecture and decision documents, the current open pull request, and recent commits. Treat the repository state as authoritative and update this file when the project phase changes.## Current Phase — Media Asset Integration

### PR #17 — Media Processing Jobs

Merged into `main` as commit `57e04d490933aca6dc26871dd69e7ee160b5dce6`.

- Added persistent `MediaProcessingJob` state and transitions
- Created a processing job after `DownloadJob.COMPLETED`
- Ran FFprobe inspection through the existing `animedownloader-media` library
- Persisted the media path and structured probe metadata
- Exposed processing status and latest Episode processing state through the API
- Added retry without re-downloading
- Kept processing state independent from terminal DownloadJob state
- Added a manual trigger for processing an existing completed DownloadJob
- Verified Backend, Frontend, and Integration CI successfully

The processing job remains the execution/history record rather than the primary representation of the current playable media.

### PR #18 — Media Asset / Episode Integration

Merged into `main` as commit `b3222e675a51e9d2d95faea06b15b2a2794391ef`.

- Added a persistent `MediaAsset` entity with one canonical asset per Episode
- Materialized the successful processing output path into the Episode media asset
- Kept MediaAsset metadata minimal; detailed probe data remains on `MediaProcessingJob`
- Exposed Episode media information through `GET /api/episodes/{episode_id}/media`
- Kept DownloadJob and MediaProcessingJob as execution/history records
- Made media asset materialization part of the same transaction as processing completion
- Verified Backend, Frontend, and Integration CI successfully

### PR #19 — Current Media Metadata

Merged into `main`.

- Added current user-facing media metadata to `MediaAsset`
- Added container format, duration, size, codecs, dimensions, frame rate, and metadata refresh timestamp
- Added a typed `MediaAssetMetadata` value object to keep the domain independent from the technical media package
- Projected the existing typed FFprobe result into MediaAsset metadata
- Re-inspected existing assets whose metadata had not yet been materialized
- Kept the full FFprobe snapshot on `MediaProcessingJob` without duplicating it into MediaAsset
- Expanded `GET /api/episodes/{episode_id}/media` to expose current media metadata
- Kept metadata materialization atomic with processing completion
- Added API, worker, unit, and PostgreSQL-backed integration coverage

## Media Pipeline Roadmap

The next features continue to build the current MediaAsset representation without turning `MediaProcessingJob` into a container for every media concern.

### PR #20 — Subtitle Track Integration

In development on `feature/subtitle-track-integration`.

Goal: represent subtitle tracks as part of the current media asset without implementing extraction yet.

Scope:

- Add a persistent subtitle-track entity associated with MediaAsset
- Materialize current embedded subtitle-stream metadata from FFprobe during media processing
- Store track language, title, default/forced flags, codec or format, and source/path information needed by later extraction/normalization stages
- Define the relationship between MediaAsset and its current subtitle tracks
- Extend the media API with current subtitle-track information
- Add migration and domain/API coverage

Out of scope:

- Subtitle extraction from containers
- Subtitle OCR or format conversion
- Subtitle normalization rules
- HLS/DASH subtitle packaging

### PR #21 — Subtitle Extraction / Normalization

Goal: materialize embedded or external subtitle sources into a normalized application representation.

Scope:

- Extract subtitle tracks discovered by FFprobe
- Normalize supported subtitle formats
- Persist normalized subtitle artifacts and processing status
- Make extraction retryable without re-downloading the video
- Update current MediaAsset subtitle-track state atomically

Out of scope:

- Transcoding/remuxing of video or audio
- Player UI

### PR #22 — Chapter / Attachment / Sprite Integration

Goal: persist the remaining useful inspection metadata that belongs to the current media asset.

Scope:

- Persist chapter metadata
- Represent embedded attachments where useful to playback or later processing
- Define sprite/thumbnail metadata needed by the future player pipeline
- Expose the current media-related assets through focused API models

Out of scope:

- Video transcoding
- HLS/DASH packaging
- Player implementation

### PR #23 — Transcoding / Remuxing

Goal: introduce derived-media generation while preserving MediaAsset as the current playable-media identity.

Scope:

- Define processing jobs for remux/transcode operations
- Persist derived media paths and output metadata
- Re-inspect generated output and update MediaAsset atomically
- Support retry/failure history

### PR #24 — HLS / DASH Packaging

Goal: derive streaming representations from the current media asset.

Scope:

- Add packaging jobs and generated manifests/segments
- Track package state separately from the source MediaAsset
- Keep source-media metadata and streaming-package metadata distinct

### PR #25 — SeaweedFS / Media Storage

Goal: move durable media artifacts from local development storage to SeaweedFS.

Scope:

- Define storage abstraction and media-object lifecycle
- Upload current media and derived artifacts
- Preserve local filesystem support for development
- Add cleanup/error handling without coupling storage concerns to processing jobs

### PR #26 — Player / Playback

Goal: expose the current MediaAsset and its derived streaming/subtitle resources to the frontend player.

Scope:

- Add playback-oriented API
- Integrate media metadata and subtitle tracks
- Support direct-file playback and later packaged playback as separate paths
- Add focused player UI and API coverage

## Planned Follow-up

After PR #20, immediate next work is PR #21, focused on subtitle extraction and normalization. Extraction and normalization remain separate from track persistence so the current MediaAsset representation can stabilize before introducing processing logic.

## Handoff Notes

For a new development session, use this document together with `AGENTS.md`, the relevant architecture and decision documents, the current open pull request, and recent commits. Treat the repository state as authoritative and update this file when the project phase changes.
