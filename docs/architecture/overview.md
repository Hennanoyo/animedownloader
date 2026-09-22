# Architecture Overview

## System

`animedownloader` is a web application composed of:

- React SPA
- FastAPI API
- Taskiq worker
- PostgreSQL
- Redis when required
- SeaweedFS
- ffmpeg/ffprobe
- Torrent/download infrastructure

Conceptually:

Browser → FastAPI → Taskiq Worker → external/download/media infrastructure

PostgreSQL stores durable application state and media metadata. Redis is used for transient events such as progress notifications when required.

## Application Boundaries

### Web

`web/apps` contains executable frontend applications.

`web/libs` contains reusable frontend functionality such as API clients, UI components, and media-player infrastructure.

### Server

`server/apps` contains executable backend applications.

`server/domains` contains business behavior and use cases.

`server/libs` contains reusable technical infrastructure.

## Jobs

Downloads and media processing are long-running jobs.

The browser should receive job state from the API and realtime events when available. A disconnected browser must be able to reconnect and reconstruct the current state from persistent data.

## Storage

Database rows refer to media files by storage object key. Public URLs are derived at the API boundary using environment-backed storage configuration.
