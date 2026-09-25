export const downloadJobStatuses = [
  "pending",
  "downloading",
  "paused",
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


export interface DownloadJobListItem extends DownloadJob {
  anime_id: string;
  anime_title: string;
  episode_number: number;
  episode_title: string;
}

export interface DownloadJobListResponse {
  items: DownloadJobListItem[];
  page: number;
  page_size: number;
  total: number;
  has_more: boolean;
}

export interface DownloadJobListParams {
  statuses?: DownloadJobStatus[];
  page?: number;
  pageSize?: number;
  signal?: AbortSignal;
}
