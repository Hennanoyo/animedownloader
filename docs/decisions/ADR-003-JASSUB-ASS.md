# ADR-003: Normalize Subtitles to ASS for JASSUB

## Status

Accepted

## Context

The frontend uses JASSUB for browser-side ASS subtitle rendering, while downloaded media can contain several subtitle formats.

## Decision

Treat ASS as the canonical subtitle representation for subtitles rendered through JASSUB.

Preserve ASS/SSA subtitles where possible. Convert other supported subtitle formats to ASS in the backend normalization pipeline.

Preserve font attachments required by subtitle styles.

## Consequences

- Frontend subtitle handling has one canonical rendering format.
- Conversion logic is isolated in backend/media infrastructure.
- Source subtitle fidelity must be tested, especially for positioning, styles, timing, and other ASS semantics.
