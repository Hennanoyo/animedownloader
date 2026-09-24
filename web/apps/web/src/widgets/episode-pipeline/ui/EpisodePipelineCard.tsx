import { useState } from "react";
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
  const [expanded, setExpanded] = useState(
    pipeline.active || hasPipelineFailure(pipeline),
  );
  const pipelineId = "episode-pipeline-" + episode.id;

  return (
    <article className={styles.card}>
      <div className={styles.topRow}>
        <Link
          className={styles.thumbnailLink}
          to="/episodes/$episodeId"
          params={{ episodeId: episode.id }}
          aria-label={episode.title + " thumbnail"}
        >
          <div
            className={styles.thumbnail}
            aria-hidden="true"
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
        </Link>

        <div className={styles.heading}>
          <p className={styles.episodeNumber}>
            Episode #{episode.episode_number}
          </p>
          <h3>
            <Link
              className={styles.titleLink}
              to="/episodes/$episodeId"
              params={{ episodeId: episode.id }}
            >
              {episode.title}
            </Link>
          </h3>
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

        <div className={styles.actions}>
          {!downloadActive ? (
            <EpisodeDownloadControl episodeId={episode.id} compact />
          ) : null}
        </div>
      </div>

      <div className={styles.pipelineSection}>
        <Button
          className={styles.pipelineToggle}
          onPress={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          aria-controls={pipelineId}
        >
          <span className={styles.pipelineSummaryLine}>
            {stages.map((stage, index) => (
              <span key={stage.id} className={styles.summaryStage}>
                {index > 0 ? (
                  <span className={styles.summaryConnector} aria-hidden="true">
                    →
                  </span>
                ) : null}
                <span
                  className={styles.summaryDot}
                  data-status={getStageStatus(stage.id, pipeline)}
                  aria-hidden="true"
                />
                <span>{stage.label}</span>
                <span className={styles.summaryStatus}>
                  {formatCompactStatus(getStageStatus(stage.id, pipeline))}
                </span>
              </span>
            ))}
          </span>
          <span className={styles.toggleLabel}>
            {expanded ? "Hide details" : "Show details"}
            <span className={styles.toggleIcon} aria-hidden="true">
              {expanded ? "⌃" : "⌄"}
            </span>
          </span>
        </Button>

        {expanded ? (
          <div id={pipelineId} className={styles.stages} aria-label="Media pipeline status">
            {stages.map((stage) => {
              const stageStatus = getStageStatus(stage.id, pipeline);
              const completed = stageStatus === "completed";
              const current = pipeline.current_stage === stage.id;
              const action = getStageAction(stage.id, pipeline);

              return (
                <div key={stage.id} className={styles.stageWrap}>
                  <div
                    className={styles.stage}
                    data-status={stageStatus}
                    data-current={current}
                    data-completed={completed}
                  >
                    <div className={styles.stageHeader}>
                      <div className={styles.stageTitle}>
                        <span className={styles.stageDot} aria-hidden="true" />
                        <span>{stage.label}</span>
                      </div>
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

                    {stage.id === "download" && pipeline.download.error_message ? (
                      <p className={styles.error}>{pipeline.download.error_message}</p>
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

                    {action ? (
                      <Button
                        className={styles.stageAction}
                        onPress={() => void retryMutation.mutateAsync()}
                        isDisabled={retryMutation.isPending}
                      >
                        {retryMutation.isPending
                          ? "Starting..."
                          : action}
                      </Button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        ) : null}
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

      {retryMutation.isError ? (
        <span className={styles.actionError} role="alert">
          {retryMutation.error instanceof Error
            ? retryMutation.error.message
            : "Failed to continue the pipeline."}
        </span>
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

function getStageAction(
  stage: PipelineCurrentStage,
  pipeline: EpisodePipelineSummary,
): "Continue" | "Retry" | null {
  const actionableStage = getActionableStage(pipeline);
  if (actionableStage === null || actionableStage !== stage) {
    return null;
  }

  if (
    stage === "processing" &&
    (pipeline.processing.status === "pending" ||
      pipeline.processing.status === "failed")
  ) {
    return pipeline.processing.status === "failed" ? "Retry" : "Continue";
  }

  if (
    stage === "preview" &&
    (pipeline.thumbnail.status === "pending" ||
      pipeline.thumbnail.status === "failed")
  ) {
    return pipeline.thumbnail.status === "failed" ? "Retry" : "Continue";
  }

  if (
    stage === "streaming" &&
    (pipeline.streaming.status === "pending" ||
      pipeline.streaming.status === "failed")
  ) {
    return pipeline.streaming.status === "failed" ? "Retry" : "Continue";
  }

  return null;
}

function getActionableStage(
  pipeline: EpisodePipelineSummary,
): PipelineCurrentStage | null {
  if (pipeline.download.status !== "completed") {
    return null;
  }

  if (
    pipeline.processing.status === "pending" ||
    pipeline.processing.status === "failed"
  ) {
    return "processing";
  }

  if (
    pipeline.processing.playable_ready &&
    (pipeline.thumbnail.status === "pending" ||
      pipeline.thumbnail.status === "failed")
  ) {
    return "preview";
  }

  if (
    pipeline.processing.playable_ready &&
    (pipeline.streaming.status === "pending" ||
      pipeline.streaming.status === "failed")
  ) {
    return "streaming";
  }

  return null;
}

function hasPipelineFailure(pipeline: EpisodePipelineSummary): boolean {
  return (
    pipeline.download.status === "failed" ||
    pipeline.processing.status === "failed" ||
    pipeline.thumbnail.status === "failed" ||
    pipeline.streaming.status === "failed"
  );
}

function formatCompactStatus(status: PipelineStageStatus): string {
  switch (status) {
    case "completed":
      return "✓";
    case "not_started":
      return "—";
    case "failed":
      return "!";
    case "pending":
      return "…";
    default:
      return "";
  }
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
