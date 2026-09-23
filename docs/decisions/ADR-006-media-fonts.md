# ADR-006: Reuse Embedded Fonts by Content Identity

## Status

Accepted

## Context

Matroska media can embed font files used by ASS/SSA subtitles. The same font can appear in multiple media files, and attachment filenames are not a reliable identity because different files may share a name or the same binary may be packaged under different names.

## Decision

Represent extracted fonts as reusable MediaFont resources.

- Store the original attachment filename as the font name metadata.
- Store a SHA-256 digest of the extracted bytes as the canonical identity.
- Enforce uniqueness by SHA-256 so identical font binaries are stored once.
- Let each media attachment reference the reusable MediaFont resource when it represents a font.
- Keep the font storage path independent from the per-MediaAsset attachment occurrence.

Font filename/name remains searchable metadata, not the uniqueness key.

## Consequences

- Identical fonts can be reused by multiple MediaAssets.
- Different files with the same filename remain distinguishable.
- Subtitle and player pipelines can resolve font references without duplicating the binary.
- A later font parser can add family/style metadata without changing attachment identity.
