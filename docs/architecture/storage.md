# Storage Architecture

## Storage Abstraction

Media artifacts are accessed through a small storage abstraction rather than hard-coding a storage provider into the media-processing domain.

The current implementations are:

- `LocalStorage` for development and deterministic tests
- `SeaweedFSStorage` for runtime object storage

The backend selects the implementation through the `STORAGE_BACKEND` setting. Local storage remains the default so existing development data and workflows continue to work during the migration.

## Object Keys

Persist durable derived media artifacts as provider-independent object keys:

```
playable/{media_asset_id}/{job_id}.mp4
streaming/{media_variant_id}/master.m3u8
streaming/{media_variant_id}/manifest.mpd
streaming/{media_variant_id}/{quality}/index.m3u8
streaming/{media_variant_id}/{quality}/init.mp4
streaming/{media_variant_id}/{quality}/s/{segment}.m4s
subtitles/{media_asset_id}/{track_id}.ass
thumbnails/{media_asset_id}/sprite.jpg
thumbnails/{media_asset_id}/sprite.vtt
fonts/{prefix}/{sha256}.ttf
attachments/{media_asset_id}/{attachment_id}-{filename}
```

Do not persist environment-specific public URLs as the canonical database representation.

Existing database columns named `path`, `normalized_path`, `extracted_path`, and similar fields may contain object keys for derived artifacts during this incremental migration. A later schema cleanup may rename these fields to `object_key` where that improves clarity.

## Processing and Storage

Media processing should use temporary local staging paths for FFmpeg and then upload successful outputs through the storage abstraction.

The persistent workflow is:

```
source media
  ↓
FFmpeg / local staging
  ↓
Storage.put_file(...)
  ↓
persist object key in PostgreSQL
```

For packaging jobs, a playable object is materialized to temporary local storage before FFmpeg packaging:

```
Storage
  ↓
temporary playable file
  ↓
CMAF packaging
  ↓
temporary package tree
  ↓
Storage.put_file(...)
```

This keeps FFmpeg independent from the storage provider and makes upload failures distinguishable from media-processing failures.

## Source Media

The canonical downloaded `MediaAsset.path` remains a local filesystem path in this phase because media inspection, subtitle extraction, and attachment extraction still read the shared download/media volumes directly.

The storage migration therefore focuses first on durable derived artifacts. Existing local absolute paths remain readable by `LocalStorage` so previously generated artifacts can continue to be consumed while the migration proceeds.

Migrating source media itself to object storage is a separate lifecycle concern.

## SeaweedFS

SeaweedFS is the project's object/file storage backend.

Application code should access SeaweedFS through the storage adapter rather than depending directly on SeaweedFS APIs throughout the repository.

The current adapter uses the SeaweedFS Filer HTTP interface and keeps the application dependency surface small.

## Endpoints

Use environment-backed configuration for at least:

- internal storage endpoint used by backend containers
- public storage/media endpoint used when constructing browser-facing URLs

Example:

```
STORAGE_BACKEND=seaweedfs
STORAGE_INTERNAL_URL=http://storage:8888
STORAGE_PUBLIC_URL=https://media.example.com
```

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

## Testing

Storage adapters have deterministic tests for upload, materialization, deletion, existence checks, key validation, and failure handling.

The Docker Compose integration workflow also runs a storage smoke test against the actual SeaweedFS service.

The existing media-streaming smoke test uses the same storage abstraction, so it can validate HLS/DASH package contents without assuming a local filesystem backend.
