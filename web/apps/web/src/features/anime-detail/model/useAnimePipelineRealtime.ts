import type { QueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { JobProgressEvent } from "../../../shared/api/jobProgress";
import { useJobProgressRealtime } from "../../../shared/api/useJobProgressRealtime";
import type {
  AnimePipeline,
  EpisodePipelineSummary,
} from "../../../entities/anime/model/pipeline";
import type { DownloadJob } from "../../../entities/download/model/types";

const animePipelineQueryKey = (animeId: string) =>
  ["anime-pipelines", animeId] as const;

const realtimeMediaJobTypes = new Set([
  "media-processing",
  "media-preparation",
  "media-packaging",
]);

export function useAnimePipelineRealtime({
  animeId,
  enabled,
}: {
  animeId: string;
  enabled: boolean;
}) {
  const queryClient = useQueryClient();
  const onReady = useCallback(
    () =>
      queryClient.refetchQueries({
        queryKey: animePipelineQueryKey(animeId),
        type: "active",
      }),
    [animeId, queryClient],
  );
  const onEvent = useCallback(
    (event: JobProgressEvent) => {
      applyAnimePipelineEvent(queryClient, animeId, event);
    },
    [animeId, queryClient],
  );

  return useJobProgressRealtime({
    enabled,
    onReady,
    onEvent,
  });
}

export function applyAnimePipelineEvent(
  queryClient: QueryClient,
  animeId: string,
  event: JobProgressEvent,
): void {
  const queryKey = animePipelineQueryKey(animeId);

  if (realtimeMediaJobTypes.has(event.job_type)) {
    void queryClient.invalidateQueries({ queryKey });
    return;
  }

  if (event.job_type !== "download" || !isPipelineStageStatus(event.status)) {
    return;
  }

  const current = queryClient.getQueryData<AnimePipeline>(queryKey);
  if (!current) {
    return;
  }

  const episodeIndex = current.episodes.findIndex(
    (episode) => episode.download.job_id === event.job_id,
  );
  if (episodeIndex < 0) {
    void queryClient.invalidateQueries({ queryKey });
    return;
  }

  const episode = current.episodes[episodeIndex];
  if (
    episode.download.updated_at !== null &&
    event.emitted_at.getTime() <= Date.parse(episode.download.updated_at)
  ) {
    return;
  }

  const nextEpisode: EpisodePipelineSummary = {
    ...episode,
    download: {
      ...episode.download,
      status: event.status,
      downloaded_bytes:
        event.downloaded_bytes ?? episode.download.downloaded_bytes,
      total_bytes: event.total_bytes ?? episode.download.total_bytes,
      error_message: event.error_message,
      updated_at: event.emitted_at.toISOString(),
    },
  };
  nextEpisode.current_stage = getCurrentStage(nextEpisode);
  nextEpisode.active = isPipelineActive(nextEpisode);

  const episodes = [...current.episodes];
  episodes[episodeIndex] = nextEpisode;
  queryClient.setQueryData<AnimePipeline>(queryKey, {
    ...current,
    episodes,
  });

  const latestQueryKey = [
    "download-jobs",
    "latest",
    nextEpisode.episode_id,
  ] as const;
  queryClient.setQueryData<DownloadJob>(latestQueryKey, (job) => {
    if (!job || job.id !== event.job_id) {
      return job;
    }
    return {
      ...job,
      status: event.status,
      downloaded_bytes:
        event.downloaded_bytes ?? job.downloaded_bytes,
      total_bytes: event.total_bytes ?? job.total_bytes,
      error_message: event.error_message,
      updated_at: event.emitted_at.toISOString(),
      completed_at:
        event.status === "completed" ||
        event.status === "failed" ||
        event.status === "cancelled"
          ? job.completed_at
          : job.completed_at,
    };
  });

  if (
    event.status === "completed" ||
    event.status === "failed" ||
    event.status === "cancelled"
  ) {
    void queryClient.invalidateQueries({ queryKey });
  }
}

function isPipelineStageStatus(
  status: string,
): status is EpisodePipelineSummary["download"]["status"] {
  return [
    "not_started",
    "pending",
    "processing",
    "downloading",
    "completed",
    "failed",
    "paused",
    "cancelled",
  ].includes(status);
}

function getCurrentStage(
  episode: EpisodePipelineSummary,
): EpisodePipelineSummary["current_stage"] {
  if (
    episode.download.status === "pending" ||
    episode.download.status === "downloading"
  ) {
    return "download";
  }
  if (
    episode.processing.status === "pending" ||
    episode.processing.status === "processing"
  ) {
    return "processing";
  }
  if (
    episode.thumbnail.status === "pending" ||
    episode.thumbnail.status === "processing"
  ) {
    return "preview";
  }
  if (
    episode.streaming.status === "pending" ||
    episode.streaming.status === "processing"
  ) {
    return "streaming";
  }
  return null;
}

function isPipelineActive(episode: EpisodePipelineSummary): boolean {
  return [
    episode.download.status,
    episode.processing.status,
    episode.subtitles,
    episode.attachments,
    episode.streaming.status,
    episode.thumbnail.status,
  ].some(
    (status) =>
      status === "pending" ||
      status === "processing" ||
      status === "downloading",
  );
}
