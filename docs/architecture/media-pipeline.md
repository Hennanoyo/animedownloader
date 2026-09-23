# Media Pipeline

## Goal

Convert downloaded anime media into browser-oriented streaming assets while preserving useful source metadata, chapters, subtitles, and attachments.

## Pipeline

```
Source MKV
  ↓
Inspect (ffprobe / media tooling)
  ↓
Decide whether video encoding is required
  ├─ acceptable HEVC → remux/package where possible
  └─ otherwise       → transcode to HEVC
  ↓
CMAF/fMP4 media assets
  ├─ HLS manifest (.m3u8)
  └─ DASH manifest (.mpd)
```

HLS and DASH should reference the same underlying encoded media assets whenever practical. A separate video encode must not be introduced merely because two manifests are required.

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

## Chapters and Metadata

Relevant source metadata and chapter information should be extracted and persisted as structured artifacts/metadata.

## Thumbnails

Generate a thumbnail sprite together with timing information suitable for hover/seek previews in the React player.

A sprite image plus WebVTT timing/region metadata is the preferred conceptual representation.

## Outputs

A media item may expose assets such as:

- HLS manifest
- DASH manifest
- CMAF/fMP4 segments
- normalized ASS subtitle files
- reusable extracted subtitle fonts (content-addressed by SHA-256)
- chapter metadata
- media metadata
- thumbnail sprite/timing data
