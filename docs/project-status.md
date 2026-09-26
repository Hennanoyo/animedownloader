## Current Phase

The project has completed Anime/Episode management, persistent torrent download execution, download controls, media inspection, current MediaAsset metadata, subtitle integration and normalization, chapter/embedded attachment integration, media storage, CMAF/HLS/DASH packaging, and the initial player/playback delivery layer.

The Unified Media Preparation & Realtime Stage Progress phase is complete. PR #23 through PR #35 are merged. Release Discovery & Episode Ingestion is complete through PR #40. Media Source Lifecycle & Recovery is complete through PR #42. Release Provenance & Explicit Replacement is complete through PR #43. Anime Release Preferences & Candidate Ranking is complete through PR #44; the next phase is Periodic Release Discovery & Candidate Inbox.

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

**Merged into `main` as commit `421442f28991b5d80270e8ab0ab5f4ea98d36c3e`.**

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

**Merged into `main` as commit `6ff2d8630fb726af0ab055e300fe4c9d0e564ea3`.**

Goal: make playback failures recoverable and keep playback API queries stable during normal player interaction.

Initial scope:

- add a bounded Playback API retry policy
- avoid unnecessary Playback API refetches when the browser window regains focus
- add an explicit retry action when the Playback API cannot be loaded
- distinguish media-source failures from other player errors
- allow a failed media engine to be reattached through an explicit retry action
- add deterministic browser coverage for media playback recovery

Current implementation:

- Added bounded Playback API retries and disabled unnecessary window-focus refetches
- Added Playback API and media-source retry actions
- Added media-engine error callbacks for asynchronous HLS.js/dash.js failures
- Added one internal recovery attempt for fatal HLS.js network/media errors before surfacing the failure
- Added automatic playback source fallback from HLS to DASH to direct MP4 when a selected source fails
- Added deterministic unit/browser coverage for source fallback and media-engine error handling
- Refresh Playback data when the player mounts instead of reusing a fresh cache entry
- Re-fetch Playback data from the media retry action so replaced media URLs are not retried indefinitely
- Reset prior source-failure exclusions when refreshed Playback data replaces the video source
- Added browser coverage for replacing an exhausted media source through Playback refresh

Planned follow-up within the same phase:

- none; proceed to the next playback/platform phase after PR #29


### PR #30 — Media Pipeline Integration & Anime Detail UX

**Merged into `main` as commit `0ed5f512ce362937ca64a892729efa369ef1e8b6`.**

Goal: complete the user-visible Episode media pipeline from Download through playable media, thumbnail readiness, HLS/DASH packaging, and playback readiness, while replacing the wide Episode table with a pipeline-oriented detail view.

Current implementation:

- Added `GET /api/animes/{anime_id}/pipeline` as a UI-oriented batched summary over DownloadJob, MediaProcessingJob, MediaPreparationJob, MediaAsset, playable MediaVariant, streaming package, subtitle/attachment processing, and thumbnail state
- Kept execution/history records separate while projecting them into stable Episode pipeline stages
- Fixed the worker packaging handoff so a completed MediaPreparationJob resolves its own `variant_id` directly before creating the MediaPackagingJob
- Preserved automatic worker chaining from completed download → media processing → preparation → CMAF/HLS/DASH packaging
- Added HLS/DASH readiness to the Episode pipeline summary while allowing direct playable MP4 playback as soon as the current playable variant is ready
- Added Anime detail Episode cards with a connected `Download → Processing → Preview → Streaming` visual flow
- Added a highlighted current stage with reduced-motion-aware animation and completed-stage connector effects
- Added preparation progress as artifact completion state: Processing reports 0/100% for playable readiness, and Preview reports 0/100% for sprite readiness
- Added active-only TanStack Query polling at 2-second intervals and cache invalidation after download actions
- Added Playwright coverage for the Anime detail pipeline UI, including stage progress bars and sprite preview
- Added backend coverage for pipeline-state aggregation and the transition from Processing to Preview when playable media is ready
- Updated the media E2E smoke to verify that the normal download pipeline reaches HLS/DASH packaging before validating stored streaming artifacts

Important implementation note:

- `MediaPreparationJob` is the shared orchestration unit for playable media and thumbnails, but `FFmpegMediaPreparationProcessor` currently executes those two FFmpeg operations sequentially rather than in one shared FFmpeg filter graph. This PR exposes honest stage-level completion rather than inventing a fine-grained percentage.
- HLS and DASH continue to reuse the same CMAF/fMP4 segments; packaging does not duplicate video encoding.

Planned follow-up:

- Do not expand this PR with real-time FFmpeg progress unless profiling shows that coarse stage completion is insufficient.
- Proceed to the next Download Management UX work rather than adding more media-pipeline surface area.

### PR #31 — Download Management UX

**Merged into `main` as commit `7ae502f484fd1563c1f02d61bf543676699e9662`.**

Goal: provide a coherent place to monitor and control downloads across Episodes instead of requiring users to manage each download only from the Anime detail Episode card.

Completed implementation:

- Added `GET /api/download-jobs` with repeated `status` filters and bounded page/page_size pagination
- Joined DownloadJob with Episode and Anime so the management response contains stable display context without N+1 frontend requests
- Added a dedicated `/downloads` route and primary navigation entry
- Added All / Active / Failed / History filters through TanStack Router search state
- Added responsive download job cards with Pause / Resume / Cancel / Retry / Download again / Delete record actions
- Reused the existing Episode download mutations and invalidates both detail and management query caches after actions
- Limited management polling to `pending` / `downloading`; paused and terminal entries do not poll
- Added backend, frontend API/query, and Playwright coverage, including a narrow viewport horizontal-overflow regression check
- Verified the full repository GitHub Actions CI after resolving browser-test selector and formatting issues

### PR #32 — Realtime Job Progress

**Merged into `main` as commit `134f7623ed15e3eb5b6a29651419e57f773ce08d`.**

Goal: replace active Download Manager polling with a shared realtime progress transport that can later serve long-running download and media-processing jobs without making PostgreSQL the event bus.

Planned architecture:

```
Download worker / media worker
        │
        │ progress event
        ▼
      Redis
   (Pub/Sub channel)
        │
        ▼
   FastAPI WebSocket
        │
        ▼
 Download Manager / future Media Pipeline UI
```

Initial scope:

- Define a small versioned progress-event schema that identifies job type, job ID, status, downloaded/total bytes where available, optional progress percent, and emitted timestamp
- Add a Redis publisher abstraction in the infrastructure layer rather than coupling domain services directly to Redis
- Publish coarse download progress events from the worker without writing every progress sample to PostgreSQL
- Add a FastAPI WebSocket endpoint that subscribes to the relevant Redis channel and forwards validated events to connected browsers
- Keep the existing HTTP download-job list/detail endpoints as the initial snapshot and recovery source
- Update the Download Manager so the initial page load uses HTTP state, then active cards consume WebSocket updates and invalidate/refetch on reconnect or terminal transitions
- Preserve the existing Pause / Resume / Cancel / Retry / Download again / Delete record semantics
- Add focused Redis/event unit tests, WebSocket API tests, frontend event/state tests, and Playwright coverage for live progress and reconnect behavior

Design constraints:

- PostgreSQL remains the durable source of truth, not a per-progress-event transport
- Redis Pub/Sub is treated as ephemeral delivery; a reconnect must recover from the HTTP snapshot instead of assuming missed events can be replayed
- Event publishing must not make a download or media job fail when realtime delivery is unavailable
- Keep the event contract generic enough to support both DownloadJob and MediaProcessingJob later
- Do not move FFmpeg/media-pipeline processing logic into the WebSocket layer
- Avoid introducing queue scheduling/prioritization or concurrency controls in this PR

Out of scope:

- Persistent event history or replayable event storage
- Automatic download scheduling/prioritization
- Major changes to FFmpeg preparation or CMAF packaging
- Multi-resolution transcoding
- UI redesign beyond wiring realtime state into the existing Download Manager

Acceptance criteria:

- Active Download Manager cards stop using periodic status polling during healthy WebSocket connectivity
- A newly connected client renders the current HTTP snapshot before applying realtime events
- Download progress changes are reflected without a full page refresh
- Terminal transitions remove/update the active card without waiting for the polling interval
- WebSocket disconnect/reconnect recovers from an HTTP snapshot and does not leave stale progress indefinitely
- Redis/WebSocket delivery failures do not change the durable DownloadJob outcome
- Existing Backend, Frontend, Browser, and Integration CI remains green

### PR #33 — Realtime Anime Detail Pipeline

**Merged into `main` as commit `e07dd0c087cb1731a52e8b285df8e0dfe21a0a44`.**

- Extended the shared realtime `JobProgressEvent` flow to media processing, preparation, and packaging jobs
- Reused the existing WebSocket transport for both Download Manager and Anime detail
- Replaced healthy Anime detail pipeline polling with realtime updates and HTTP snapshot recovery on connect/reconnect
- Kept download byte-progress updates cache-local while media-stage lifecycle changes trigger pipeline snapshot refreshes
- Added backend, frontend, and Playwright coverage for realtime Anime detail progress
- Preserved PostgreSQL as the durable source of truth and Redis Pub/Sub as ephemeral delivery

The PR deliberately reports coarse media-stage lifecycle progress rather than inventing fine-grained FFmpeg percentages.

## Media Preparation Optimization & Realtime Stage Progress

The media pipeline currently reaches the correct user-visible stages, but the shared preparation path still decodes the source video twice when both playable media and thumbnail previews are required. The realtime transport also currently carries only coarse 0/100 lifecycle signals for media jobs.

### PR #34 — Unified Media Preparation & Realtime Stage Progress

**Merged into `main` as commit `44c8c649fbdca983d83db5c055b84707f1edb2cf`.**

Goal: make the Processing → Preview pipeline perform at most one source-video decode when both outputs are required, while exposing honest realtime progress for Processing, Preview, and Streaming.

Scope:

- Replace the current combined preparation implementation's two sequential FFmpeg executions with one FFmpeg invocation whenever playable media and thumbnails are both required
- Use a shared input/decode path with separate output/filter branches for playable media and thumbnail generation
- Preserve the current REMUX/TRANSCODE planning behavior: skip video transcoding when the source already satisfies the playable constraints, while still generating thumbnails from the source
- Keep thumbnail VTT generation and derived-artifact persistence independent of the playable MediaVariant state even though their source decode is shared
- Extend the FFmpeg runner with incremental progress reporting based on FFmpeg's machine-readable progress output
- Emit realtime progress events during media preparation rather than only at 0% and 100%
- Add stage/substage information to realtime progress events so one MediaPreparationJob can update both the Processing and Preview UI stages without inventing duplicate jobs
- Add realtime progress for CMAF packaging and expose it as Streaming stage progress
- Update the Anime detail pipeline cache directly from realtime media-stage progress while retaining HTTP snapshot recovery for connection/reconnect
- Keep durable PostgreSQL job state coarse-grained; do not persist every FFmpeg progress sample as a database write
- Add deterministic FFmpeg runner/processor tests and Playwright coverage for progressing Processing, Preview, and Streaming stages

Design constraints:

- When both playable and thumbnail artifacts are missing, the source video should be decoded once and branched inside a single FFmpeg process
- The shared filter graph must keep memory bounded; do not introduce a design that accumulates the entire source or an unbounded thumbnail frame queue
- Thumbnail sampling remains bounded by the existing sprite capacity and interval rules
- REMUX must not unnecessarily decode the video for the playable output; only the thumbnail branch should require video decoding
- PostgreSQL remains the durable source of truth; Redis Pub/Sub remains ephemeral delivery
- Realtime progress is an observation channel, not durable job state
- Reconnects must recover job status and artifact completion from the HTTP pipeline snapshot even when an intermediate progress percentage was missed
- Do not change HLS/DASH artifact layout or encode additional video representations
- Preserve the existing Download Manager realtime transport and behavior

Realtime progress model:

```
FFmpeg / worker
    │
    ├─ Processing progress ─────→ shared JobProgressEvent(stage=processing)
    │
    ├─ Preview progress ────────→ shared JobProgressEvent(stage=preview)
    │
    └─ Packaging progress ─────→ shared JobProgressEvent(stage=streaming)
                                      │
                                      ▼
                               Redis Pub/Sub
                                      │
                                      ▼
                              FastAPI WebSocket
                                      │
                                      ▼
                              Anime Detail UI
```

For a combined preparation job, Processing and Preview progress may advance from the same decoded input timeline because both outputs are produced by the same FFmpeg invocation. A displayed percentage represents progress through the source media being processed, not a claim that the two outputs consume equal work.

Out of scope:

- Automatic release discovery or Episode ingestion
- Automatic download scheduling
- Fine-grained queue/concurrency management
- New media artifacts or storage backends
- Multi-resolution transcoding
- Playback/player redesign

Acceptance criteria:

- When both playable media and thumbnails are required, only one FFmpeg process reads/decodes the source video
- A source that only needs REMUX skips unnecessary transcoding while still producing thumbnails
- Processing and Preview show live percentage updates during preparation when realtime connectivity is healthy
- Streaming shows live packaging percentage updates
- Realtime progress updates do not create per-sample PostgreSQL writes
- WebSocket disconnect/reconnect recovers correct durable stage state through the existing HTTP snapshot
- Partial artifact completion and retry remain independent
- Existing Download Manager realtime behavior remains green
- Backend, Frontend, Browser, and Integration CI remains green

### Next Phase — Release Discovery & Episode Ingestion

The next feature phase reduces manual Episode creation by turning external release discovery into a controlled, reviewable ingestion workflow while keeping raw Nyaa RSS/search results ephemeral.

See `docs/architecture/release-discovery.md` and `docs/decisions/ADR-007-release-discovery-and-versioned-parser-profiles.md` for the accepted architecture and design constraints.

### PR #35 — Release Discovery Foundation

Goal: establish the provider-neutral release model, generic parsing pipeline, versioned release-group profiles, and deterministic parser validation without yet coupling discovery to Episode persistence.

Scope:

- Preserve raw provider releases as ephemeral data; do not introduce a release-result cache
- Keep Nyaa behind the existing provider/client boundary
- Add a generic parser that extracts high-confidence series, episode, group, and technical metadata
- Add `parsed` / `ambiguous` / `unparsed` / `unsupported` outcomes
- Add release-group identity and versioned Parser Profiles
- Store declarative parser rules, including regex patterns, as validated database configuration
- Add draft/active/retired profile lifecycle
- Add parser-rule validation with representative multi-sample tests
- Keep profile versions immutable after activation
- Add deterministic parser/profile tests

Out of scope:

- Anime matching
- Episode ingestion
- Release discovery UI
- Automatic downloads
- Search-profile execution

Acceptance criteria:

- Representative Nyaa-style release titles are parsed deterministically
- Unknown release groups safely fall back to the generic parser
- Ambiguous episode forms are not silently converted into normal Episodes
- A new parser profile can be drafted and validated without changing application code
- Active parser behavior is reproducible through an explicit profile version

### PR #35 — Release Discovery Foundation

**Merged into `main` as commit `16a59a76f21cee1b4b238d41533d0b53ae91eaba`.**

- Added provider-neutral `ParsedRelease` results and deterministic generic release-title parsing
- Added versioned release-group Parser Profile entities with draft/active/retired lifecycle
- Added declarative parser rules, validation, and representative multi-sample validation
- Added release parser persistence migration and Alembic registration
- Kept raw provider search results ephemeral and outside persistent release storage
- Added deterministic parser/profile test coverage

Out of scope and deferred to the following discovery PRs: Search Profile execution, Anime matching, Episode ingestion, discovery UI, and automatic downloads.

### PR #36 — Release Search Profiles & Discovery

**Merged into `main` as commit `d38941b6f4bd431d492c9f9b13ab41d6fa966183`.**

- Added versioned Search Profiles for release groups
- Added constrained progressive Nyaa query-template execution
- Merged and deduplicated raw results in memory while keeping provider results ephemeral
- Applied the existing generic/parser-profile pipeline to discovered releases
- Added `GET /api/releases/discover` for parsed discovery candidates
- Added Anime-detail release discovery UI with title/group/episode/resolution/codec constraints
- Added backend/frontend/browser coverage for discovery behavior
- Confirmed Backend, Frontend, Browser, and Integration GitHub Actions CI after fixing release deduplication and Browser smoke selector issues

Out of scope and deferred to the next discovery PRs: Episode persistence, explicit Anime matching/acceptance workflow, automatic downloads, periodic scheduling, and automatic release ranking.

### PR #37 — Anime Titles & Single-Query Discovery Refinement

Status: **Merged** (`2b36773525f21ecefe1b5a5f49e5f319d5b1d74f`)

Goal: make Anime title metadata useful for release discovery and make every discovery action explicit and user-controlled.

Scope:

- Keep `Anime.title` as the representative display title
- Add PostgreSQL JSONB `Anime.titles` for typed alternate forms such as `romaji`, `jp`, `ko`, and `en`
- Use `titles.romaji` as the Anime-detail Nyaa search default, falling back to `title` when unavailable
- Keep the search title editable and transient; search edits never update Anime metadata
- Execute exactly one Nyaa query per discovery action
- Replace progressive query-template fallback with an ordered search-field recipe
- Let users enable/disable and reorder search fields before searching
- Show the exact rendered query before and after searching
- Simplify the discovery API to a single `query` result and warnings
- Cover title metadata, field ordering, single-query behavior, and the romaji search default

Design constraints:

- The active Search Profile provides a default field order for callers that do not provide their own request order
- No automatic retry or progressive broadening after a zero-result search
- Alternate title edits in the discovery panel are never persisted to Anime
- Raw Nyaa search results remain ephemeral

Out of scope:

- Anime matching and Episode ingestion
- Automatic periodic discovery
- Additional providers
- Media-processing/player changes

### PR #38 — Release Discovery UX Refinement

Goal: make the Anime-detail release-discovery workflow fast and explicit without changing the single-query Search Profile architecture.

Scope:

- replace arrow-only field reordering with drag-and-drop field rows
- retain keyboard-accessible reordering through the focused drag handle
- keep field enable/disable state as an explicit checkbox with a visible check mark
- move all search-value editing inline into each Search field row
- add an Anime-title source selector for Romaji, Japanese, Korean, English, Main title, or Custom
- prefer `titles.romaji` as the default Anime-detail search title, falling back to `title`
- keep Custom/search-title edits transient and never persist them to Anime
- show live query preview from the exact current field order, enabled state, and values
- add Browser coverage for title-source selection, inline editing, field reordering, and single-query discovery

Design constraints:

- Search Profile data remains responsible only for the default field recipe
- Current UI edits are request-local overrides and do not mutate Search Profile or Anime metadata
- Discovery still executes exactly one provider query per click
- Preserve the provider → Release → Parse → Match → Ingest boundaries

Out of scope:

- Anime matching and Episode ingestion
- parser/search profile administration
- automatic discovery or downloads
- media/player changes

### PR #39 — Release Profile Operations & Drift Detection

**Merged into `main` as commit `5a5d495ec72429abbbc916068a5ab1649151cff0`.**

Goal: make release-profile maintenance a first-class operational workflow after real-world releases have accumulated.

Completed scope:

- Add parser profile administration UI
- Show profile version history and activation state
- Store/review representative parser samples
- Compare active and draft parser results
- Add parser-health aggregates and manual drift signals
- Allow creation of a new profile version from observed failures
- Add deterministic profile validation and regression coverage
- Use consistent ComboBox-based discovery values, with persisted release-group suggestions
- Refine discovery and parser-profile UI with compact controls, constrained popovers, dark-theme scrollbars, responsive layouts, and expandable rule cards
- Validate the final browser UI with Playwright coverage at desktop and narrow responsive viewports

Design constraints:

- Drift detection is an observation/maintenance aid, not automatic profile activation
- A detected drift must be reviewed and validated before becoming active
- Do not persist raw RSS feeds merely to calculate profile health
- Active parser profiles remain immutable

### PR #40 — Anime Matching & Episode Ingestion

**Merged into `main` as commit `fa4132143767dfe44abb7c65d648791adea26745`.**

Goal: turn parsed, ephemeral release candidates into explicit, reviewable Anime/Episode associations and transactional Episode state changes without starting downloads automatically.

Implementation order:

1. Define deterministic Anime matching around the existing `Anime.title` + structured `Anime.titles` metadata.
2. Return explicit match states: matched, ambiguous, or unmatched, with candidate Anime records and match evidence suitable for user review.
3. Introduce a provider-neutral ingestion contract that carries parsed release fields plus provenance already required by the Episode model.
4. Implement transactional Episode ingestion for:
   - new Anime + episode association when an existing Anime is explicitly selected;
   - idempotent re-ingestion of the same external release using stable source identity;
   - explicit replacement-candidate results when the episode number already exists with a different release.
5. Preserve user-maintained Episode fields and never reset DownloadJob/media-processing state during re-ingestion.
6. Keep discovery, matching, and ingestion separate from DownloadJob creation; accepting a release must not automatically start a torrent.
7. Add backend API coverage for match ambiguity, idempotency, replacement candidates, and transactional rollback/conflict cases.
8. Add frontend review/acceptance UI only after the matching/ingestion API contract is stable.

Design constraints:

- Raw provider search results remain ephemeral.
- Matching is conservative and deterministic; do not auto-create an Anime from an unmatched release.
- Year/season can be supporting evidence but release publication time is not authoritative Anime air metadata.
- A different release for an already populated episode must never silently replace existing media-bearing state.
- Re-ingestion may update mutable release provenance but must not overwrite user-edited Episode fields without explicit user acceptance.
- Episode ingestion does not create or start a DownloadJob.

Out of scope:

- Automatic release ranking
- Periodic discovery
- Automatic downloads
- Additional providers
- Media/player changes

### PR #41 — Media Source Reconciliation & Recovery

**Merged into `main` as commit `17ac0260a19ad32fa7ba1f6e47986655ded9bdcf`.**

Goal: make the boundary between completed downloads and physical source media explicit and recoverable without silently re-downloading or deleting user data.

Implementation order:

1. Define a deterministic filesystem source-resolution contract for a completed DownloadJob directory:
   - missing directory;
   - no supported media file;
   - exactly one supported media file;
   - multiple supported media files.
2. Reuse the same source-resolution logic in media processing so source failures are classified consistently.
3. Reconcile completed DownloadJob records when the worker starts:
   - when a completed job has a valid source but no MediaProcessingJob, recreate the missing processing handoff and enqueue it;
   - keep already-created processing jobs untouched;
   - leave missing/ambiguous sources unresolved and emit actionable diagnostics.
4. Keep source reconciliation idempotent and safe under worker restarts; never create duplicate MediaProcessingJobs.
5. Add deterministic unit coverage for source resolution and recovery decisions plus a lightweight worker recovery integration path.

Design constraints:

- A completed DownloadJob remains the authoritative download execution/history record.
- Source recovery must not automatically create or start a new torrent in this phase.
- Missing source data must be observable before any destructive cleanup or re-download policy is introduced.
- Source paths remain local filesystem representations; durable derived artifacts continue to use storage object keys.
- Existing MediaProcessingJob and downstream media state are preserved.
- Reconciliation is a recovery mechanism for lost handoff messages, not a replacement for explicit user controls.

Out of scope for PR #41:

- automatic re-download of missing source media
- automatic deletion of orphaned source directories
- source-media migration to SeaweedFS
- release discovery, matching, or player changes

The following PR can add explicit user-facing source recovery actions and a conservative orphan/cleanup policy once source state is observable and reconciled.

### PR #42 — User-facing Media Source Recovery & Orphan Cleanup

**Merged into `main` as commit `e23e3fa71994e9bf2839dece3a789f37e11245ee`.**

- Added deterministic user-facing downloaded-source inspection and recovery
- Added explicit ambiguous-source selection with path traversal protection
- Added explicit media reprocessing and explicit re-download without deleting prior history
- Added orphan download-source inventory and destructive cleanup with DownloadJob/MediaProcessingJob/MediaAsset reference protection
- Added Anime detail source review and Downloads-page orphan maintenance UI
- Documented source lifecycle and recovery safety boundaries
- Added Backend, Frontend, Browser, and Integration coverage



Goal: make local downloaded source state inspectable and recoverable from the application while keeping re-download and destructive cleanup explicitly user-controlled.

Implementation order:

1. Expose the latest completed DownloadJob source state through a provider-neutral API:
   - no completed download;
   - missing source directory;
   - no supported media;
   - exactly one source;
   - multiple candidate sources.
2. Allow explicit source selection for ambiguous downloads using a validated path relative to the DownloadJob directory.
3. Allow explicit media reprocessing without re-downloading when a valid source exists.
4. Allow explicit re-download when the completed source is missing or unusable; never trigger it automatically from source reconciliation.
5. Add an orphan-source inventory for UUID-named download directories that are not referenced by DownloadJob or MediaProcessingJob state.
6. Add explicit orphan deletion with path containment and persistent-reference checks.
7. Integrate source recovery into Anime detail Episode pipeline and expose orphan maintenance from Downloads.
8. Add deterministic backend/frontend coverage for source states, safe path validation, recovery actions, and orphan cleanup.

Design constraints:

- DownloadJob remains the authoritative download execution/history record.
- A recovery action must never silently replace existing completed media state.
- Source paths are local filesystem representations and are never persisted as storage object keys.
- User-selected source paths are normalized to relative paths inside the DownloadJob directory.
- Orphan cleanup is never automatic.
- A directory referenced by a MediaProcessingJob remains protected even if its original DownloadJob record was deleted.
- Re-download creates a new DownloadJob and never deletes the old download history.
- Derived SeaweedFS/local storage artifacts are outside source-directory cleanup.

Out of scope:

- automatic source cleanup
- automatic release ranking or discovery scheduling
- source migration to object storage
- additional media/player features

### PR #43 — Release Provenance & Explicit Replacement

**Merged into `main` as commit `b71bad344a5120dc02c92e534ff9bca7756741bf`.**

- Persisted nullable `Episode.release_group_id` provenance with `SET NULL` semantics
- Connected known enabled ReleaseGroup identities during release ingestion without auto-creating groups
- Added explicit release replacement with history guards for DownloadJob, MediaProcessingJob, and MediaAsset
- Preserved user-maintained Episode title and execution/media state during replacement
- Added discovery UI and regression coverage for replacement candidates
- Added release provenance/replacement safety rules to `AGENTS.md`

### PR #44 — Anime Release Preferences & Candidate Ranking

**Merged into `main` as commit `70716665f6a10a0b79679cc7ee23c55763201a25`.**

- Added optional per-Anime release preferences for ReleaseGroup, resolution, video codec, and source
- Added GET/PATCH preference APIs and Anime-detail preference editing
- Added deterministic, explainable preference ranking to release discovery
- Kept unset preference fields neutral and seeders as a post-score tie-breaker
- Preserved discovery-only safety boundaries: no automatic downloads, Episode replacement, or provenance mutation
- Added backend, frontend, browser, and integration regression coverage


Goal: let each Anime store optional release preferences and use them to produce deterministic, explainable discovery ordering without starting downloads or silently changing Episode state.

Implementation order:

1. Add an optional per-Anime release preference record for ReleaseGroup, resolution, video codec, and source.
2. Expose GET/PATCH preference APIs and a compact Anime-detail preference editor using existing React Aria ComboBox controls.
3. Extend release discovery requests with the target Anime ID so ranking can be evaluated against that Anime's preferences.
4. Add deterministic preference scoring with explicit reasons for group/resolution/codec/source matches.
5. Keep unconfigured preference fields neutral; do not penalize candidates when a preference is unset.
6. Sort discovery candidates only when preferences exist, with stable parser status, seeder count, and title tie-breakers after preference score.
7. Show the ranking score/reasons next to each discovered release so users can understand why results moved.
8. Add backend/API/Browser regression coverage.

Design constraints:

- Preferences are hints for discovery ordering, not automatic download policy.
- Unknown ReleaseGroups are never created from preference editing.
- Current Nyaa seeders are only a deterministic tie-breaker; they must not override explicit preference matches.
- Ranking never creates DownloadJobs, replaces Episodes, or mutates Episode provenance.
- Automatic discovery scheduling, automatic release selection, and automatic downloads remain future phases.

Out of scope:

- periodic discovery scheduling
- automatic release selection
- automatic downloads
- new providers
- media/player changes

## Next Phase — Periodic Release Discovery & Candidate Inbox

The next phase should move discovery from a purely user-triggered operation toward a persistent, reviewable candidate workflow without crossing into automatic Episode mutation or downloads.

### PR #45 — Periodic Release Discovery & Candidate Inbox

Goal: periodically execute the existing Anime discovery recipe, retain normalized candidates as a deliberate application record, and give the user a reviewable inbox while keeping provider RSS/search payloads ephemeral.

Implementation order:

1. Define a provider-neutral persisted discovery-candidate snapshot containing Anime identity, normalized release/provenance fields, parser/match outcome, observed-at timestamp, and the ranking explanation produced by the current preference scorer.
2. Keep raw Nyaa RSS/search results ephemeral; persist only normalized candidate data needed for review, deduplication, and later acceptance.
3. Add deterministic candidate identity/deduplication so repeated discovery runs do not create an unbounded duplicate stream for the same external release.
4. Add an explicit discovery-run record with started/completed/failed state and lightweight diagnostics, separate from DownloadJob and Episode state.
5. Add a Taskiq-backed periodic discovery trigger with per-Anime scheduling configuration, but keep scheduling limited to candidate collection.
6. Expose recent discovery runs and candidate inbox APIs with filters for new, reviewed, accepted, rejected, and stale candidates.
7. Add Anime-detail and/or dedicated discovery-inbox UI showing ranking score/reasons, parser/match state, observed time, and an explicit review action.
8. Preserve all existing safety boundaries: candidate collection never creates Episodes, replaces existing media, or starts DownloadJobs automatically.
9. Add backend, frontend, browser, and integration coverage for idempotency, scheduler behavior, candidate retention, and restart safety.

Design constraints:

- Raw provider search/RSS responses remain ephemeral and must not become a general release-result cache.
- Persisted candidates are normalized review records, not authoritative Episode records.
- Candidate identity must be stable across repeated discovery runs for the same provider release.
- Ranking remains deterministic and explainable using Anime release preferences; preference changes must not rewrite historical candidate observations silently.
- Periodic discovery must be restart-safe and must not enqueue duplicate runs for the same Anime/time window.
- Candidate collection never starts a DownloadJob and never performs automatic Episode ingestion or replacement.
- Retention/cleanup must be explicit and bounded so the inbox cannot grow without limit.

Out of scope:

- automatic candidate acceptance/selection
- automatic downloads
- new release providers
- media/player changes

### Following phase — Explicit Candidate Acceptance & Download Policy

After the candidate inbox is stable, introduce a separate user-controlled acceptance flow that can create/update Episodes only through explicit review, followed by DownloadJob creation under an explicit download policy. Automatic selection and automatic download scheduling should remain separate from candidate collection so each transition is observable and recoverable.

## Handoff Notes:

PR #44 is merged into `main`. The next development branch should start from merge commit `70716665f6a10a0b79679cc7ee23c55763201a25` and implement PR #45 Periodic Release Discovery & Candidate Inbox.

## Handoff Notes

For a new development session, use this document together with `AGENTS.md`, the relevant architecture and decision documents, the current repository state, and recent commits. Treat the repository state as authoritative and update this file whenever the development phase changes.
