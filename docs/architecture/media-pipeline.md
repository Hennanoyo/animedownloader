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

Playable media and thumbnails are derived from the same source in a shared FFmpeg execution whenever both are needed.

For a TRANSCODE operation, the source video is decoded once and split into:

- a playable branch encoded to HEVC
- a thumbnail branch sampled, scaled, padded, and tiled into a sprite

For a REMUX operation, compatible video/audio streams are copied directly into MP4 while the thumbnail branch is decoded for frame extraction.

The preparation job records durable execution state and a source path/metadata snapshot. Playable and thumbnail artifact state remains independent so retries can process only the missing artifact after a partial failure.

The generated playable MP4 is re-inspected with FFprobe before the `MediaVariant` is marked ready.

## Hardware Acceleration

The default video encoder setting is `auto`. Before a transcode, the worker runs a small real FFmpeg probe for `hevc_nvenc`. When the probe succeeds, the preparation job uses NVENC; when the GPU, driver, NVIDIA Container Toolkit, or NVENC encoder is unavailable, the worker transparently falls back to CPU `libx265`.

This keeps the media pipeline portable without making GPU availability a prerequisite. Docker Compose can expose the GPU to the worker when available, but the application itself does not require a GPU-specific encoder setting. The repository's `just up` performs this host/container capability check automatically and uses the GPU Compose overlay only when the NVIDIA device is usable; otherwise it starts the normal CPU worker.

The NVENC path keeps the existing software decode and thumbnail filter graph. This is intentional: the shared thumbnail pipeline requires CPU-side filtering, and avoiding CUDA-frame filter negotiation keeps the preparation path portable and predictable. NVENC still removes the HEVC encoding workload from the CPU, which is the expensive part of TRANSCODE. The CPU fallback remains unchanged.

FFmpeg subprocesses are started in their own POSIX process group so timeout or task cancellation can terminate the complete FFmpeg process tree instead of leaving an orphaned encoder/decoder running after a worker failure. The development worker defaults to one Taskiq child process because media transcoding is resource-intensive; `TASKIQ_WORKERS` can be increased explicitly when the host has capacity for concurrent jobs.

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

Thumbnail generation is part of the shared media preparation pass when a playable artifact is also required. If the playable artifact is already current, thumbnail-only retry uses the thumbnail processor without regenerating the playable file.

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
