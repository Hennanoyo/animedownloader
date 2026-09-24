import { Link } from "@tanstack/react-router";
import { Button } from "react-aria-components";
import type { Episode } from "../../../entities/anime/model/types";
import type {
  EpisodePipelineSummary,
  PipelineCurrentStage,
  PipelineStageStatus,
} from "../../../entities/anime/model/pipeline";
import { useRetryEpisodePipeline } from "../../../features/anime-detail/model/useAnimePipeline";
import EpisodeDownloadControl from "../../../features/episode-download/ui/EpisodeDownloadControl";
import styles from "./EpisodePipelineCard.module.scss";

interface Props {
  episode: Episode;
  pipeline: EpisodePipelineSummary;
}

const stages: { id: PipelineCurrentStage; label: string }[] = [
  { id: "download", label: "Download" },
  { id: "processing", label: "Processing" },
  { id: "preview", label: "Preview" },
  { id: "streaming", label: "Streaming" },
];

export default function EpisodePipelineCard({ episode, pipeline }: Props) {
  const retryMutation = useRetryEpisodePipeline(episode.id);
  const downloadActive =
    pipeline.download.status === "pending" ||
    pipeline.download.status === "downloading" ||
    pipeline.download.status === "paused";
  const retryAction = getRetryAction(pipeline);

  return (
    <article className={styles.card}>
      <div className={styles.topRow}>
        <div
          className={styles.thumbnail}
          role="img"
          aria-label={episode.title + " thumbnail"}
          style={
            pipeline.thumbnail.url
              ? { backgroundImage: `url("${pipeline.thumbnail.url}")` }
              : undefined
          }
        >
          {pipeline.thumbnail.url ? null : (
            <span className={styles.thumbnailPlaceholder}>No preview</span>
          )}
        </div>

        <div className={styles.heading}>
          <div>
            <p className={styles.episodeNumber}>
              Episode #{episode.episode_number}
            </p>
            <h3>{episode.title}</h3>
            <p className={styles.source}>
              {episode.source_url ? (
                <a href={episode.source_url} target="_blank" rel="noreferrer">
                  {episode.source}
                </a>
              ) : (
                episode.source
              )}
              {episode.size ? " · " + episode.size : ""}
            </p>
          </div>
        </div>

        <div className={styles.actions}>
          {pipeline.playback_ready ? (
            <Link
              className={styles.playButton}
              to="/episodes/$episodeId"
              params={{ episodeId: episode.id }}
            >
              Play
            </Link>
          ) : null}

          {retryAction ? (
            <Button
              className={styles.retryButton}
              onPress={() => void retryMutation.mutateAsync()}
              isDisabled={retryMutation.isPending}
              aria-label={retryAction.ariaLabel}
            >
              {retryMutation.isPending ? "Starting..." : retryAction.label}
            </Button>
          ) : null}

          {!downloadActive ? (
            <EpisodeDownloadControl episodeId={episode.id} compact />
          ) : null}

          {retryMutation.isError ? (
            <span className={styles.actionError} role="alert">
              {retryMutation.error instanceof Error
                ? retryMutation.error.message
                : "Failed to continue the pipeline."}
            </span>
          ) : null}
        </div>
      </div>

      <div className={styles.stages} aria-label="Media pipeline status">
        {stages.map((stage, index) => {
          const stageStatus = getStageStatus(stage.id, pipeline);
          const completed = stageStatus === "completed";
          const current = pipeline.current_stage === stage.id;
          return (
            <div key={stage.id} className={styles.stageWrap}>
              {index > 0 ? (
                <span
                  className={styles.connector}
                  data-completed={isPreviousStageCompleted(index, pipeline)}
                  aria-hidden="true"
                />
              ) : null}
              <div
                className={styles.stage}
                data-status={stageStatus}
                data-current={current}
                data-completed={completed}
              >
                <span className={styles.stageDot} aria-hidden="true" />
                <div className={styles.stageHeader}>
                  <span>{stage.label}</span>
                  <span className={styles.status} data-status={stageStatus}>
                    {formatStatus(stageStatus)}
                  </span>
                </div>
                {stage.id === "processing" ? (
                  <StageProgress
                    label="Preparation"
                    value={pipeline.processing.progress_percent}
                  />
                ) : null}
                {stage.id === "preview" ? (
                  <StageProgress
                    label="Sprite"
                    value={pipeline.thumbnail.progress_percent}
                  />
                ) : null}
                {stage.id === "streaming" ? (
                  <p className={styles.detail}>
                    {formatStreamingDetail(pipeline)}
                  </p>
                ) : null}
                {stage.id === "processing" && pipeline.processing.error_message ? (
                  <p className={styles.error}>{pipeline.processing.error_message}</p>
                ) : null}
                {stage.id === "preview" && pipeline.thumbnail.error_message ? (
                  <p className={styles.error}>{pipeline.thumbnail.error_message}</p>
                ) : null}
                {stage.id === "streaming" && pipeline.streaming.error_message ? (
                  <p className={styles.error}>{pipeline.streaming.error_message}</p>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      <div className={styles.extras}>
        <span>Subtitles: {formatStatus(pipeline.subtitles)}</span>
        <span>Attachments: {formatStatus(pipeline.attachments)}</span>
        {pipeline.download.error_message ? (
          <span className={styles.error}>{pipeline.download.error_message}</span>
        ) : null}
      </div>

      {downloadActive ? (
        <div className={styles.downloadPanel} aria-label="Download progress">
          <div className={styles.downloadPanelHeader}>
            <span>Download progress</span>
            <span>Live transfer</span>
          </div>
          <EpisodeDownloadControl episodeId={episode.id} />
        </div>
      ) : null}
    </article>
  );
}

interface StageProgressProps {
  label: string;
  value: number;
}

function StageProgress({ label, value }: StageProgressProps) {
  return (
    <div className={styles.progressBlock}>
      <div className={styles.progressMeta}>
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div
        className={styles.progressTrack}
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
      >
        <div className={styles.progressFill} style={{ width: value + "%" }} />
      </div>
    </div>
  );
}

function getStageStatus(
  stage: PipelineCurrentStage,
  pipeline: EpisodePipelineSummary,
): PipelineStageStatus {
  switch (stage) {
    case "download":
      return pipeline.download.status;
    case "processing":
      return pipeline.processing.status;
    case "preview":
      return pipeline.thumbnail.status;
    case "streaming":
      return pipeline.streaming.status;
  }
}

function isPreviousStageCompleted(
  index: number,
  pipeline: EpisodePipelineSummary,
): boolean {
  const previous = stages[index - 1];
  return previous !== undefined && getStageStatus(previous.id, pipeline) === "completed";
}

function getRetryAction(
  pipeline: EpisodePipelineSummary,
): { label: "Continue" | "Retry"; ariaLabel: string } | null {
  if (pipeline.download.status !== "completed") {
    return null;
  }

  const candidates: Array<{
    stage: PipelineCurrentStage;
    status: PipelineStageStatus;
    ready: boolean;
  }> = [
    {
      stage: "processing",
      status: pipeline.processing.status,
      ready: true,
    },
    {
      stage: "preview",
      status: pipeline.thumbnail.status,
      ready: pipeline.processing.playable_ready,
    },
    {
      stage: "streaming",
      status: pipeline.streaming.status,
      ready: pipeline.processing.playable_ready,
    },
  ];

  for (const candidate of candidates) {
    if (
      candidate.ready &&
      (candidate.status === "pending" || candidate.status === "failed")
    ) {
      const action = candidate.status === "failed" ? "Retry" : "Continue";
      return {
        label: action,
        ariaLabel: action + " " + candidate.stage,
      };
    }
  }

  return null;
}

function formatStatus(status: PipelineStageStatus): string {
  return status
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatStreamingDetail(pipeline: EpisodePipelineSummary): string {
  return (
    (pipeline.streaming.hls_ready ? "HLS ready" : "HLS pending") +
    " · " +
    (pipeline.streaming.dash_ready ? "DASH ready" : "DASH pending")
  );
}
