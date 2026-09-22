# Storage Architecture

## SeaweedFS

SeaweedFS is the project's object/file storage backend.

Application code should access storage through a dedicated storage service or adapter instead of depending directly on SeaweedFS APIs everywhere.

## Database Representation

Persist an object key:

```
media/123/hls/master.m3u8
media/123/video/init.mp4
media/123/subtitles/0.ass
media/123/thumbnails/sprite.jpg
```

Do not persist environment-specific public URLs as the canonical database representation.

## Endpoints

Use environment-backed configuration for at least:

- internal storage endpoint used by backend containers
- public storage/media endpoint used when constructing browser-facing URLs

Example:

```
STORAGE_INTERNAL_URL=http://storage:8888
STORAGE_PUBLIC_URL=https://media.example.com
```

The concrete environment variable names may evolve with the application's settings module.

## URL Construction

The API may derive a browser-facing URL from:

```
public endpoint + object key
```

at response time.

This keeps the database independent of Docker network names, reverse proxies, deployment domains, or local development URLs.

## Browser Access

Whether browsers access SeaweedFS directly or through an authenticated API/media gateway is an application-boundary decision and should not leak into domain code.

Keep this choice behind the storage/media delivery layer.
