export const mediaSourceStatuses = [
  "not_available",
  "found",
  "missing_directory",
  "no_media",
  "ambiguous",
] as const;

export type MediaSourceStatus = (typeof mediaSourceStatuses)[number];

export const mediaSourceDownloadStatuses = [
  "pending",
  "downloading",
  "paused",
  "completed",
  "failed",
  "cancelled",
] as const;

export type MediaSourceDownloadStatus =
  (typeof mediaSourceDownloadStatuses)[number];

export const mediaProcessingStatuses = [
  "pending",
  "processing",
  "completed",
  "failed",
] as const;

export type MediaProcessingStatus = (typeof mediaProcessingStatuses)[number];

export interface MediaSourceCandidate {
  path: string;
}

export interface EpisodeMediaSource {
  episode_id: string;
  download_job_id: string | null;
  download_status: MediaSourceDownloadStatus | null;
  status: MediaSourceStatus;
  root: string | null;
  selected_path: string | null;
  candidates: MediaSourceCandidate[];
  processing_job_id: string | null;
  processing_status: MediaProcessingStatus | null;
}

export interface MediaSourceActionResult {
  stage: "download" | "processing";
  job_id: string;
  status: "pending";
}

export interface MediaSourceOrphan {
  directory_id: string;
  path: string;
}
