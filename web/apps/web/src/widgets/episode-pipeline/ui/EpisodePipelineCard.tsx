import { Link } from "@tanstack/react-router";
import type { Episode } from "../../../entities/anime/model/types";
import type {
  EpisodePipelineSummary,
  PipelineStageStatus,
} from "../../../entities/anime/model/pipeline";
import EpisodeDownloadControl from "../../../features/episode-download/ui/EpisodeDownloadControl";
import styles from "./EpisodePipelineCard.module.scss";

interface Props {
  episode: Episode;
  pipeline: EpisodePipelineSummary;
}

export default function EpisodePipelineCard({ episode, pipeline }: Props) {
  return (
    <article className={styles.card}>
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

      <div className={styles.content}>
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

        <div className={styles.stages} aria-label="Media pipeline status">
          <PipelineStage
            label="Download"
            status={pipeline.download.status}
            detail={formatDownloadProgress(pipeline.download)}
          />
          <PipelineStage
            label="Processing"
            status={pipeline.processing.status}
            detail={
              pipeline.processing.playable_ready
                ? "Playable ready"
                : pipeline.processing.error_message ?? undefined
            }
          />
          <PipelineStage
            label="Streaming"
            status={pipeline.streaming.status}
            detail={formatStreamingDetail(pipeline)}
          />
          <PipelineStage
            label="Preview"
            status={pipeline.thumbnail.status}
          />
        </div>

        <div className={styles.extras}>
          <span>Subtitles: {formatStatus(pipeline.subtitles)}</span>
          <span>Attachments: {formatStatus(pipeline.attachments)}</span>
          {pipeline.download.error_message ? (
            <span className={styles.error}>
              {pipeline.download.error_message}
            </span>
          ) : null}
          {pipeline.processing.error_message ? (
            <span className={styles.error}>
              {pipeline.processing.error_message}
            </span>
          ) : null}
          {pipeline.streaming.error_message ? (
            <span className={styles.error}>
              {pipeline.streaming.error_message}
            </span>
          ) : null}
          {pipeline.thumbnail.error_message ? (
            <span className={styles.error}>
              {pipeline.thumbnail.error_message}
            </span>
          ) : null}
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
        <EpisodeDownloadControl episodeId={episode.id} />
      </div>
    </article>
  );
}

interface PipelineStageProps {
  label: string;
  status: PipelineStageStatus;
  detail?: string;
}

function PipelineStage({ label, status, detail }: PipelineStageProps) {
  return (
    <div className={styles.stage}>
      <div className={styles.stageHeader}>
        <span>{label}</span>
        <span className={styles.status} data-status={status}>
          {formatStatus(status)}
        </span>
      </div>
      {detail ? <p>{detail}</p> : null}
    </div>
  );
}

function formatStatus(status: PipelineStageStatus): string {
  return status
    .replaceAll("_", " ")
    .replace(/\bw/g, (letter) => letter.toUpperCase());
}

function formatDownloadProgress(download: {
  status: PipelineStageStatus;
  downloaded_bytes: number;
  total_bytes: number | null;
}): string | undefined {
  if (download.total_bytes === null || download.total_bytes === 0) {
    return download.status === "completed"
      ? formatBytes(download.downloaded_bytes)
      : undefined;
  }

  return (
    formatBytes(download.downloaded_bytes) +
    " / " +
    formatBytes(download.total_bytes)
  );
}

function formatStreamingDetail(
  pipeline: EpisodePipelineSummary,
): string | undefined {
  if (
    pipeline.streaming.status === "not_started" ||
    pipeline.streaming.status === "failed"
  ) {
    return undefined;
  }

  const hls = pipeline.streaming.hls_ready ? "HLS" : "HLS…";
  const dash = pipeline.streaming.dash_ready ? "DASH" : "DASH…";
  return hls + " · " + dash;
}

function formatBytes(value: number): string {
  if (value < 1024) {
    return value + " B";
  }
  const units = ["KiB", "MiB", "GiB", "TiB"];
  let size = value / 1024;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return size.toFixed(size >= 10 ? 0 : 1) + " " + units[unitIndex];
}
