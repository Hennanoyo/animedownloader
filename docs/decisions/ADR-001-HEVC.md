# ADR-001: Use HEVC as the Primary Video Codec

## Status

Accepted

## Context

Storage capacity is limited relative to the media library size, while the current target playback devices support HEVC.

The project also needs browser-oriented streaming outputs.

## Decision

HEVC is the primary target video codec.

The pipeline must inspect the source first and avoid unnecessary transcoding. A source that already satisfies the target HEVC constraints should be remuxed/packaged when possible.

A future compatibility codec may be introduced later as a separate decision if deployment requirements change.

## Consequences

- Reduced storage usage compared with a comparable higher-bitrate codec profile.
- HEVC-specific browser/device compatibility must be treated as an explicit deployment assumption.
- Encoding profiles and quality settings must be documented when finalized.
