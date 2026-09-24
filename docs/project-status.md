## Current Phase

The project has completed Anime/Episode management, persistent torrent download execution, download controls, media inspection, current MediaAsset metadata, subtitle integration and normalization, chapter/embedded attachment integration, media storage, CMAF/HLS/DASH packaging, and the initial player/playback delivery layer.

The current phase is playback hardening. PR #23 through PR #28 are merged; PR #29 is the current development step.

## Completed

### PR #3 — Anime and Episode Management

Merged into `main` as commit `9a48d0c1f85b40541712275220a14eecab811a0e`.

- Persistent Anime and Episode models with PostgreSQL and Alembic
- Complete Anime and Episode CRUD API
- Episode Nyaa provenance and torrent metadata persistence
- Anime creation and catalog UI
- PostgreSQL CRUD and cascade integration coverage in CI

### PR #6 — Persistent Download Jobs

Merged into `main` as commit `734366149c0779129f00d7ae0ea19ce3cd8460f9`.

- Persistent DownloadJob state and terminal history
- One active job per Episode at the database level
- Download job API and migration
- Deterministic state/API tests and PostgreSQL migration coverage

### PR #7 — Torrent Infrastructure

Merged into `main` as commit `767ad92ce7f88f0266e2845a3d4a9833522ec80b`.

- Domain-neutral TorrentClient protocol
- qBittorrent Web API adapter
- Per-job torrent tag correlation
- qBittorrent configuration and Compose service
- Shared download volume and CI runtime verification

### PR #8 — Episode Download Execution

Merged into `main` as commit `a8610bb1cb39c508b64e9d9111b67b39412fc32f`.

- Episode download-job creation and Taskiq dispatch
- Worker-side DownloadRunner
- qBittorrent progress/state persistence
- Retry-safe torrent reuse and deterministic runner/API tests

### PR #9 — qBittorrent Pending Add Handling

Merged into `main`.

- Accepted qBittorrent pending torrent-add responses
- Added adapter coverage for pending and mixed add responses

### PR #10 — qBittorrent Environment and Download Path Fixes

Merged into `main` as commit `ce2a9f4d646c70d684603949f23fcccb6fcc302d`.

- Loaded qBittorrent API credentials from server settings
- Standardized the shared `/downloads` path
- Removed completed torrents without deleting downloaded files
- Updated local CORS origins and development/CI configuration

### PR #11 — Anime Detail and Episode List

Merged into `main`.

- Added Anime detail route and read-only detail view
- Added Episode list with download/conversion metadata
- Added focused single-Anime API coverage

### PR #12 — Anime Edit and Delete

Merged into `main`.

- Added Anime metadata editing and deletion
- Preserved existing Episodes during Anime edits
- Added frontend cache updates and API/validation coverage

### PR #13 — Episode Download UI

Merged into `main` as commit `d057a4d7c14a36caff36a25779af87abec5951b4`.

- Added DownloadJob frontend entity and API client
- Added Episode download action and progress polling
- Restored latest persisted job state after refresh
- Added completed, failed, cancelled, retry and redownload states

### PR #14 — Media Inspection Infrastructure

Merged into `main` as commit `19ae042137a5dffd2b54fd4a16a7a1433521822f`.

- Added `animedownloader-media`
- Added async FFprobe execution without a shell
- Added typed format, stream, attachment and chapter metadata
- Added deterministic inspector tests

### PR #15 — Episode Management and Release Reuse

Merged into `main` as commit `1adf634e60d66900426a5fe0e9e934b879c626a2`.

- Added Episode add/edit/delete operations from Anime detail
- Reused the Nyaa release picker for Episode creation
- Added frontend/backend mutation coverage

### PR #16 — Download Job Controls

Merged into `main` as commit `9773b092a72856dff3907079d74f2da5259beb65`.

- Added paused DownloadJob state
- Added qBittorrent pause/resume
- Added active-job cancel with partial-data removal
- Added terminal job-record deletion while retaining completed media files

## Media Pipeline

The post-download media pipeline keeps execution/history records separate from the current `MediaAsset` representation.

```
DownloadJob.COMPLETED
  → MediaProcessingJob
  → FFprobe inspection
  → current MediaAsset
      ├─ media metadata
      ├─ subtitle tracks
      ├─ chapters
      └─ embedded attachments
             └─ reusable MediaFont resources
```

### PR #17 — Media Processing Jobs

Merged into `main` as commit `57e04d490933aca6dc26871dd69e7ee160b5dce6`.

- Added persistent MediaProcessingJob state and transitions
- Created a processing job after completed downloads
- Persisted media path and structured FFprobe metadata
- Added retry without re-downloading
- Added manual processing triggers
- Kept processing state independent from DownloadJob terminal state

### PR #18 — Media Asset / Episode Integration

Merged into `main` as commit `b3222e675a51e9d2d95faea06b15b2a2794391ef`.

- Added one canonical MediaAsset per Episode
- Materialized the successful processing output path
- Exposed `GET /api/episodes/{episode_id}/media`
- Kept DownloadJob and MediaProcessingJob as execution/history records

### PR #19 — Current Media Metadata

Merged into `main`.

- Added current MediaAsset metadata for container, duration, size, codecs, dimensions and frame rate
- Added metadata refresh tracking
- Projected the typed FFprobe result into MediaAsset
- Re-inspected existing assets missing current metadata
- Kept the full FFprobe snapshot on MediaProcessingJob

### PR #20 — Subtitle Track Integration

Merged into `main` as commit `7c680f24f0f09d08d758141a865c4cc031032e1f`.

- Added persistent SubtitleTrack records owned by MediaAsset
- Materialized embedded subtitle-stream metadata from FFprobe
- Stored language, title, codec, default/forced flags and source metadata
- Exposed current subtitle tracks through the media API

### PR #21 — Subtitle Extraction / Normalization

Merged into `main` as commit `aed70a37160d8aeb8603124050f6155be812db9f`.

- Extracted embedded text subtitle tracks through FFmpeg
- Preserved ASS/SSA without re-encoding
- Normalized supported text formats to ASS
- Added per-track processing state, retry and failure isolation
- Enqueued subtitle processing after media inspection

### PR #22 — Chapter / Attachment Integration

Merged into `main` as commit `8513ed1f400eb212050463ea5f2de6427c4accfa`.

- Materialized chapter metadata from FFprobe
- Materialized embedded attachment metadata
- Extracted embedded attachments through FFmpeg
- Added per-MediaAsset attachment processing state and retry
- Added reusable MediaFont resources identified by SHA-256
- Preserved original font filenames as metadata
- Exposed chapters, attachments and referenced fonts through the media API

The attachment extractor was verified against a real downloaded MKV in the Docker runtime. A FFmpeg-specific edge case was fixed so the `dump_attachment` operation supplies a real null output and does not fail with `At least one output file must be specified`.

## Current Workflow

```
Browser
  → Nyaa search
  → select release
  → create Anime + Episodes
  → PostgreSQL
  → Anime detail / Episode management
  → create DownloadJob
  → Taskiq
  → Worker
  → TorrentClient / qBittorrent
  → DownloadJob.COMPLETED
  → MediaProcessingJob
  → FFprobe
  → MediaAsset
      → metadata
      → subtitles
      → chapters
      → attachments / fonts
      → thumbnails / WebVTT
  → CMAF streaming package
      ├─ HLS master/media playlists
      ├─ DASH MPD
      └─ shared fMP4 segments
```

## Media Pipeline Roadmap

### PR #23 — Thumbnail Sprite Integration

**Merged into `main` as commit `69184f804ad5cc872095aa632075a818a894467a`.**

Goal: generate a small thumbnail sprite and WebVTT timing metadata for player hover/seek previews, with a deterministic MKV fixture available for direct FFmpeg/media-pipeline verification.

Scope:

- Extract evenly spaced thumbnail frames from the current MediaAsset media file with FFmpeg
- Generate a sprite image without transcoding the source video
- Generate WebVTT cue/region metadata mapping playback time to sprite coordinates
- Persist the current sprite paths and generation timestamp
- Track sprite generation state independently from MediaProcessingJob terminal state
- Make generation retryable without re-downloading the source media
- Add deterministic FFmpeg unit tests and PostgreSQL/API coverage where state is exposed
- Add a deterministic 12-second MKV fixture generator containing video, audio, ASS subtitles, chapters, and an embedded attachment for media-pipeline validation

Design constraints:

- The source `MediaAsset.path` remains the input; do not create a new playable video representation
- Thumbnail generation is a derived artifact and should not change video/audio metadata
- Keep sprite generation independent from subtitle/attachment processing so a sprite failure does not invalidate those artifacts
- Prefer a small, explicit sprite metadata representation rather than duplicating the generated files in MediaAsset itself
- Keep the implementation ready for later storage migration to SeaweedFS

Out of scope:

- Video/audio transcoding or remuxing
- HLS/DASH packaging
- SeaweedFS upload
- Player UI

### PR #24 — Transcoding / Remuxing

**Merged into `main` as commit `4b77c2d9e09567ed59a43feed806dcf6198c6d79`.**

- Added persistent playable `MediaVariant` output separate from the source `MediaAsset`
- Added durable transcoding/remux job state and retry history
- Planned REMUX versus HEVC/AAC TRANSCODE from FFprobe metadata
- Generated and re-inspected playable MP4 output
- Protected derived output from stale source revisions
- Exposed playable media and transcoding job state through the API
- Verified real FFmpeg transcoding and remuxing in Integration CI and Docker runtime

### PR #25 — Shared Media Preparation

**Merged into `main` as commit `bf160e279c0c63693e736d3f836c16e6a8ceb976`.**

Goal: avoid decoding the same source video independently for playable media and thumbnail generation.

Scope:

- Replace separate thumbnail/transcoding execution with a shared media preparation job
- Run playable media generation and thumbnail sprite generation through one FFmpeg process
- Share the decoded video path during TRANSCODE operations
- Let REMUX copy compatible video/audio streams while decoding only the thumbnail branch
- Re-inspect generated playable media before marking the playable variant ready
- Keep playable and thumbnail artifact state independent so a retry can process only the missing artifact
- Preserve source path/metadata snapshots and durable preparation retry history
- Keep subtitle and attachment processing isolated from the shared video preparation path

Design constraints:

- `MediaAsset.path` remains the canonical source
- `MediaVariant` and thumbnail state remain independently consumable artifacts
- A successful common preparation pass should produce both derived artifacts from one source read
- A partial failure must not invalidate an already completed artifact
- FFmpeg execution remains behind media/infrastructure adapters

Out of scope:

- HLS/DASH packaging
- SeaweedFS upload/storage migration
- Player UI

### PR #26 — CMAF Packaging / HLS & DASH

**Merged into `main` as commit `cc46526205615587a3f818988a96d47cc956bea3`.**

- Added durable media packaging job state
- Created one CMAF representation from the current playable resolution
- Stored `master.m3u8` and `manifest.mpd` at the streaming package root
- Stored `<quality>/index.m3u8`, `<quality>/init.mp4`, and `<quality>/s/*.m4s` together
- Made HLS and DASH reference the same CMAF initialization/media segments
- Kept the data model ready for future multi-resolution representations
- Reused the current playable MediaVariant without re-encoding
- Added packaging status/retry APIs and stale-source protection
- Added a developer runtime smoke test for real Docker Compose/API/worker/FFmpeg validation
- Fixed a worker task bug discovered by runtime validation so completed packaging jobs are not incorrectly re-enqueued

Out of scope:

- Generating additional downscaled/ABR representations
- SeaweedFS storage migration
- Player UI

### PR #27 — SeaweedFS / Media Storage

Goal: move durable media artifacts from local development storage to SeaweedFS.

Scope:

- Define storage abstraction and object lifecycle
- Upload current and derived artifacts
- Preserve local filesystem support for development
- Add upload failure and cleanup handling
- Add a developer runtime smoke test that exercises the real SeaweedFS-backed media artifact path

Runtime validation:

- `just storage-smoke` verifies SeaweedFS upload/materialize/delete against the Compose service
- `just storage-media-smoke <episode-id>` verifies a newly processed Episode's stored playable media, subtitles, thumbnails, attachments/fonts, and CMAF/HLS/DASH artifacts
- `STORAGE_BACKEND=seaweedfs` is exposed through Compose for real application-path testing
- Development GPU acceleration is automatic. `just up` checks whether the worker can access an NVIDIA GPU and uses the GPU Compose overlay only when available; otherwise it starts the CPU worker. `FFMPEG_VIDEO_ENCODER=auto` probes real NVENC support per preparation job and falls back to `libx265` when unavailable. FFmpeg subprocesses use their own process groups for reliable cleanup on cancellation, and the development worker defaults to one Taskiq child process to avoid concurrent heavyweight media jobs exhausting host CPU/RAM.
- `storage-media-smoke` reports Redis pending tasks and active FFmpeg/temporary-output diagnostics when its wait timeout expires

### PR #28 — Player / Playback

**In progress on `feature/player-playback`.**

Goal: expose current media and derived resources through a playback-oriented API and consume that contract from a browser player.

Implementation order:

1. Playback API contract and browser-facing storage URLs
2. Frontend playback query/model
3. Native direct/HLS playback engine and Episode player page
4. HLS.js, dash.js, and JASSUB engine adapters
5. Custom accessible video controls, fullscreen, chapters, subtitles/fonts, and thumbnail seek preview
6. Developer-facing browser playback smoke coverage

Current implementation:

- Playback API exposes current playable media plus HLS/DASH, subtitle, font, chapter, and thumbnail resources
- Added hls.js and dash.js playback adapters alongside native playback
- Added JASSUB ASS subtitle rendering with prepared fonts
- Added HEVC-aware HLS/DASH codec signaling from the CMAF initialization segment
- Added a custom player control surface using React Aria Components Slider/Button primitives
- Replaced native video controls with play/pause, seek, volume/mute, subtitle selection, and player-level fullscreen controls
- Added thumbnail VTT loading and sprite xywh seek previews on the custom timeline
- Fullscreen targets the player container so the JASSUB subtitle canvas remains inside the fullscreen subtree
- Added a developer media-repackage command for regenerating the current CMAF package without re-downloading or re-preparing media

Completed browser validation coverage:

- Added Playwright Chromium smoke coverage with deterministic Playback API and media/fullscreen mocks
- Covered player initial focus, playback controls, keyboard ownership, controller focus/activation, text-input exceptions, page-scroll exceptions, thumbnail preview, and fullscreen
- Added a developer-facing real playback smoke using the actual Compose Playback API and media resources, including JASSUB subtitle/font loading when subtitle tracks are available
- Added CI Browser job with Chromium installation, E2E typecheck, smoke execution, and failure artifacts
- Added `just web-browser-install`, `just web-browser-check`, and `just real-playback-smoke <episode-id>`


Scope:

- Add playback-oriented API
- Integrate media metadata, chapters and subtitles
- Load thumbnail sprite/WebVTT metadata
- Support direct-file playback and packaged playback as separate paths
- Add focused, accessible player UI and API coverage

### PR #29 — Playback Hardening

**In progress on `feature/playback-hardening`.**

Goal: make playback failures recoverable and keep playback API queries stable during normal player interaction.

Initial scope:

- add a bounded Playback API retry policy
- avoid unnecessary Playback API refetches when the browser window regains focus
- add an explicit retry action when the Playback API cannot be loaded
- distinguish media-source failures from other player errors
- allow a failed media engine to be reattached through an explicit retry action
- add deterministic browser coverage for media playback recovery

Planned follow-up within the same phase:

- harden HLS/DASH engine error propagation
- refine browser codec/source capability reporting
- improve source fallback behavior
- cover stale playback artifacts and recovery after media replacement

## Handoff Notes

For a new development session, use this document together with `AGENTS.md`, the relevant architecture and decision documents, the current repository state, and recent commits. Treat the repository state as authoritative and update this file whenever the development phase changes.
