# Media Source Lifecycle

A completed `DownloadJob` records download execution/history separately from the physical source media directory. The source directory is local runtime data under `download_root/<download-job-id>`.

## Source Resolution

The shared download-domain resolver classifies a directory as:

- `found`: exactly one supported media file exists;
- `missing_directory`: the expected download directory does not exist;
- `no_media`: the directory exists but contains no supported media file;
- `ambiguous`: more than one supported media file exists.

The resolver is deterministic and is reused by the worker and API-facing recovery service.

## Explicit Recovery

A valid source can be reprocessed without creating a new torrent. An ambiguous source can be resolved by selecting a supported file using a path relative to the DownloadJob directory.

Missing or unusable source data can be re-downloaded only through an explicit user action. A re-download creates a new `DownloadJob`; prior download history is retained.

Source recovery must not silently replace a completed MediaProcessingJob or downstream MediaAsset state.

## Orphan Sources

A UUID-named directory under `download_root` is considered orphaned only when it is not referenced by either a `DownloadJob` or a `MediaProcessingJob`.

Orphan cleanup is explicit and destructive only at the source-directory level. It does not delete derived media artifacts or persistent processing history.

Deletion is rejected when the target is outside the configured download root or when persistent media state still references the directory.

## Storage Boundary

`source_path` and download directories remain local filesystem representations. Derived artifacts stored through the media storage abstraction continue to use canonical object keys and are managed independently of source-directory cleanup.
