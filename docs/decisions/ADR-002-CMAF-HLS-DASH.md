# ADR-002: Share CMAF/fMP4 Assets Between HLS and DASH

## Status

Accepted

## Context

The project needs both HLS and MPEG-DASH playback while avoiding duplicate video encodes and unnecessary duplicate media segments.

## Decision

Use a shared CMAF/fMP4 media representation where practical and generate separate HLS and DASH manifests that reference the shared media assets.

The need for multiple manifests must not by itself trigger multiple video encoding jobs.

## Consequences

- Less duplicated media data.
- One encoded media representation can serve multiple delivery protocols.
- Packaging and manifest generation become explicit stages in the media pipeline.
