export const downloadJobStatuses = [
  "pending",
  "downloading",
  "completed",
  "failed",
  "cancelled",
] as const;

export type DownloadJobStatus = (typeof downloadJobStatuses)[number];

export interface DownloadJob {
  id: string;
  episode_id: string;
  status: DownloadJobStatus;
  downloaded_bytes: number;
  total_bytes: number | null;
  attempt_count: number;
  error_message: string | null;
  started_at: Date | null;
  completed_at: Date | null;
  created_at: Date;
  updated_at: Date;
}
