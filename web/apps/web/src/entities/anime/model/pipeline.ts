export const pipelineStageStatuses = [
  "not_started",
  "pending",
  "processing",
  "downloading",
  "completed",
  "failed",
  "paused",
  "cancelled",
] as const;

export type PipelineStageStatus = (typeof pipelineStageStatuses)[number];

export interface EpisodePipelineDownload {
  status: PipelineStageStatus;
  downloaded_bytes: number;
  total_bytes: number | null;
  error_message: string | null;
}

export interface EpisodePipelineProcessing {
  status: PipelineStageStatus;
  playable_ready: boolean;
  error_message: string | null;
}

export interface EpisodePipelineStreaming {
  status: PipelineStageStatus;
  hls_ready: boolean;
  dash_ready: boolean;
  error_message: string | null;
}

export interface EpisodePipelineThumbnail {
  status: PipelineStageStatus;
  url: string | null;
  vtt_url: string | null;
  error_message: string | null;
}

export interface EpisodePipelineSummary {
  episode_id: string;
  episode_number: number;
  title: string;
  download: EpisodePipelineDownload;
  processing: EpisodePipelineProcessing;
  subtitles: PipelineStageStatus;
  attachments: PipelineStageStatus;
  streaming: EpisodePipelineStreaming;
  thumbnail: EpisodePipelineThumbnail;
  playback_ready: boolean;
  active: boolean;
}

export interface AnimePipeline {
  anime_id: string;
  episodes: EpisodePipelineSummary[];
}
