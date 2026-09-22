# Subtitle Architecture

## Canonical Browser Format

JASSUB is used for browser-side ASS subtitle rendering.

Therefore, the backend should expose a canonical ASS representation for subtitles that need JASSUB rendering.

## Input Formats

The pipeline may receive:

- ASS
- SSA
- SRT
- WebVTT
- other supported subtitle formats

ASS-compatible source subtitles should be preserved when possible.

Other supported formats are normalized to ASS before being exposed to JASSUB.

## MKV Attachments

MKV attachments can contain fonts required by ASS styles. When extracting subtitle resources, preserve relevant TrueType/OpenType font attachments and make them available to the JASSUB rendering layer.

## Responsibilities

Backend:

- extract subtitle tracks
- identify subtitle format
- normalize formats when required
- extract required font attachments
- record subtitle metadata

Frontend:

- load the canonical ASS
- load required fonts/resources
- render subtitles through JASSUB
- synchronize subtitle rendering with the active media engine
