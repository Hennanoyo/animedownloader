# Media Pipeline

## Goal

Convert downloaded anime media into browser-oriented streaming assets while preserving useful source metadata, chapters, subtitles, and attachments.

## Pipeline

```
Source media
  ↓
Inspect (ffprobe)
  ↓
Persist current MediaAsset metadata
  ↓
MediaPreparationJob
  ├─ playable media
  └─ thumbnail sprite / WebVTT
  ↓
Playable MediaVariant
  ↓
CMAF/fMP4 packaging
  ├─ master.m3u8
  ├─ manifest.mpd
  └─ shared representation assets
       ├─ <quality>/index.m3u8
       ├─ <quality>/init.mp4
       └─ <quality>/s/*.m4s
```

The downloaded `MediaAsset.path` remains the canonical source. Derived playable media and thumbnails are separate artifacts and must not mutate the source.

## Media Preparation

Playable media and thumbnails are derived from the same source. When both artifacts are required in the same preparation pass, the preferred implementation is one FFmpeg invocation with a shared input/decode path and separate output/filter branches.

For a TRANSCODE operation, the decoded video can feed both the HEVC playable encoder branch and the sampled thumbnail branch.

For a REMUX operation, the playable branch can copy compatible video/audio streams while the thumbnail branch decodes the source video; the source is still opened once by the FFmpeg process.

The preparation job records durable execution state and a source path/metadata snapshot. Playable and thumbnail artifact state remains independently consumable so a partial failure or retry can process only the missing artifact. Shared execution should improve source-read/decode efficiency without turning the thumbnail branch into an unbounded memory sink; thumbnail sampling remains bounded by the configured sprite capacity and interval.

The generated playable MP4 is re-inspected with FFprobe before the `MediaVariant` is marked ready.

## Hardware Acceleration

The default video encoder setting is `auto`. Before a transcode, the worker runs a small real FFmpeg probe for `hevc_nvenc`. When the probe succeeds, the preparation job uses NVENC; when the GPU, driver, NVIDIA Container Toolkit, or NVENC encoder is unavailable, the worker transparently falls back to CPU `libx265`.

This keeps the media pipeline portable without making GPU availability a prerequisite. Docker Compose can expose the GPU to the worker when available, but the application itself does not require a GPU-specific encoder setting. The repository's `just up` performs this host/container capability check automatically and uses the GPU Compose overlay only when the NVIDIA device is usable; otherwise it starts the normal CPU worker.

The NVENC path keeps software decoding and CPU-side thumbnail filtering. When both playable media and thumbnails are required, the HEVC encoder branch and thumbnail branch share one FFmpeg input/decode path; NVENC only moves the HEVC encoding workload off the CPU. The CPU fallback uses an explicit eight-thread encoder limit to keep resource usage bounded. The worker's automatic probe performs a real small NVENC encode rather than only checking whether the encoder is listed, because GPU visibility alone does not guarantee that the NVENC session can be initialized.

FFmpeg subprocesses are started in their own POSIX process group so timeout or task cancellation can terminate the complete FFmpeg process tree instead of leaving an orphaned encoder/decoder running after a worker failure. The development worker defaults to one Taskiq child process because media transcoding is resource-intensive; `TASKIQ_WORKERS` can be increased explicitly when the host has capacity for concurrent jobs.

The worker also reconciles active media-processing, preparation, and packaging jobs from the database when it starts. This recovers jobs whose Redis task message was lost or left pending after a worker failure; only jobs persisted as `pending` or `processing` are re-enqueued.

## Video

HEVC is the primary project codec because storage capacity is constrained and the target playback devices support HEVC.

The implementation should distinguish:

- codec inspection
- remux/package operations
- actual transcoding

Avoid transcoding a source that already satisfies the target media constraints.

## Subtitles

ASS/SSA subtitles should be preserved when compatible with JASSUB.

Other subtitle formats should be normalized to an ASS representation suitable for browser-side JASSUB rendering.

The normalization step must not accidentally discard important subtitle semantics. Embedded font references and required MKV attachments must be preserved.

Subtitle processing is kept separate from the shared video preparation process because subtitle extraction/normalization has different per-track state and retry semantics.

## Chapters and Attachments

Relevant source metadata and chapter information should be extracted and persisted as structured artifacts/metadata.

Embedded attachments are extracted separately and reusable font resources are content-addressed by SHA-256.

## Thumbnails

Generate a thumbnail sprite together with timing information suitable for hover/seek previews.

The sprite image plus WebVTT timing/region metadata is the preferred conceptual representation.

Thumbnail generation is part of the media preparation pass when a playable artifact is also required, and both outputs share one FFmpeg invocation. If the playable artifact is already current, thumbnail-only retry uses the thumbnail processor without regenerating the playable file.

## Realtime Progress

Long-running media preparation and packaging jobs expose incremental progress through the shared Redis Pub/Sub → FastAPI WebSocket transport. Progress percentages are transient observations, not durable job state.

For combined preparation, a single FFmpeg process may report the shared input timeline to both the Processing and Preview UI stages. The UI should treat this as progress through the common source-processing timeline rather than as two independent workloads. The initial zero-progress interval is presented as a preparation state rather than a misleading 0% value, because FFmpeg may not advance the output-time counter while it initializes decoders, filters, and encoders. Recovery actions for pending stages are delayed briefly so normal stage transitions do not flash a Continue button; Continue remains available when a pending stage stays unresolved.

## Outputs

A media item may expose assets such as:

- derived playable MP4 representation
- HLS manifest (.m3u8)
- DASH manifest (.mpd)
- CMAF/fMP4 segments
- normalized ASS subtitle files
- reusable extracted subtitle fonts (content-addressed by SHA-256)
- chapter metadata
- media metadata
- thumbnail sprite/timing data
