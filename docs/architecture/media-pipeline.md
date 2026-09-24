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

The default transcoder is CPU-based `libx265` so the media pipeline remains portable across CI and hosts without NVIDIA GPUs.

Development environments with an NVIDIA GPU can use `hevc_nvenc` through `compose.gpu.yaml` and the `FFMPEG_VIDEO_ENCODER` setting. The NVENC path changes only the video encoder; the shared thumbnail filter graph and AAC encoding can still use CPU resources. NVIDIA GPU access in Docker requires the host NVIDIA driver and NVIDIA Container Toolkit. The Compose GPU reservation and `video` driver capability are configured by the GPU overlay.

The GPU path is a development/runtime acceleration option, not a second media format. Both encoders continue to produce HEVC playable media and should be validated through FFprobe and the storage smoke test.

GPU preparation also enables CUDA hardware decoding. Decoded CUDA frames stay on the GPU for the playable NVENC path; only the thumbnail branch downloads frames to system memory for CPU-side sampling and sprite filters. The CPU-only path keeps its software decoder/encoder path. Both paths use the same shared filter graph safeguards: a bounded internal frame buffer and a small filter-thread limit prevent an imbalance between the full-rate playable branch and sparse thumbnail branch from growing system-memory usage without bound.

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
