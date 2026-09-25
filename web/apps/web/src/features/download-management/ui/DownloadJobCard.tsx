import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "react-aria-components";
import type { DownloadJobListItem } from "../../../entities/download/model/types";
import Icon from "../../../shared/ui/Icon";
import {
  useCancelDownloadJob,
  useCreateEpisodeDownloadJob,
  useDeleteDownloadJob,
  usePauseDownloadJob,
  useResumeDownloadJob,
} from "../../episode-download/model/useEpisodeDownload";
import styles from "./DownloadJobCard.module.scss";

interface Props {
  job: DownloadJobListItem;
}

export default function DownloadJobCard({ job }: Props) {
  const pauseMutation = usePauseDownloadJob(job.episode_id);
  const resumeMutation = useResumeDownloadJob(job.episode_id);
  const cancelMutation = useCancelDownloadJob(job.episode_id);
  const createMutation = useCreateEpisodeDownloadJob(job.episode_id);
  const deleteMutation = useDeleteDownloadJob(job.episode_id);
  const [confirm, setConfirm] = useState<"cancel" | "delete" | null>(null);

  const actionPending =
    pauseMutation.isPending ||
    resumeMutation.isPending ||
    cancelMutation.isPending ||
    createMutation.isPending ||
    deleteMutation.isPending;

  const progress = getProgress(job);

  return (
    <article className={styles.card} data-status={job.status}>
      <header className={styles.header}>
        <div className={styles.identity}>
          <Link
            className={styles.animeLink}
            to="/animes/$animeId"
            params={{ animeId: job.anime_id }}
          >
            {job.anime_title}
          </Link>
          <h2>
            <Link
              className={styles.episodeLink}
              to="/episodes/$episodeId"
              params={{ episodeId: job.episode_id }}
            >
              Episode #{job.episode_number} · {job.episode_title}
            </Link>
          </h2>
        </div>

        <span className={styles.status} data-status={job.status}>
          <StatusIcon status={job.status} />
          {getStatusLabel(job.status)}
        </span>
      </header>

      {job.status === "pending" || job.status === "downloading" ? (
        <div className={styles.progressArea}>
          <div className={styles.progressMeta}>
            <span>{job.status === "pending" ? "Queued" : "Downloading"}</span>
            <span>{progress.label}</span>
          </div>
          <div
            className={styles.progressTrack}
            role="progressbar"
            aria-label={"Download progress for " + job.episode_title}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress.percent}
          >
            <div
              className={styles.progressFill}
              style={{ width: progress.width }}
            />
          </div>
        </div>
      ) : job.status === "paused" ? (
        <p className={styles.detail}>Paused at {progress.label}.</p>
      ) : job.status === "failed" ? (
        <p className={styles.error} role="alert">
          {job.error_message ?? "Download failed."}
        </p>
      ) : (
        <p className={styles.detail}>{progress.label}</p>
      )}

      <div className={styles.actions}>
        {job.status === "downloading" ? (
          <Button
            className={styles.secondaryButton}
            aria-label={"Pause download for " + job.episode_title}
            onPress={() => pauseMutation.mutate(job.id)}
            isDisabled={actionPending}
          >
            <Icon name="pause" size={14} />
            {pauseMutation.isPending ? "Pausing..." : "Pause"}
          </Button>
        ) : null}

        {job.status === "paused" ? (
          <Button
            className={styles.primaryButton}
            aria-label={"Resume download for " + job.episode_title}
            onPress={() => resumeMutation.mutate(job.id)}
            isDisabled={actionPending}
          >
            <Icon name="play" size={14} />
            {resumeMutation.isPending ? "Resuming..." : "Resume"}
          </Button>
        ) : null}

        {job.status === "pending" ? (
          <span className={styles.mutedAction}>Waiting for worker…</span>
        ) : null}

        {job.status === "pending" ||
        job.status === "downloading" ||
        job.status === "paused" ? (
          <Button
            className={styles.dangerButton}
            aria-label={"Cancel download for " + job.episode_title}
            onPress={() => setConfirm("cancel")}
            isDisabled={actionPending}
          >
            <Icon name="x" size={14} />
            Cancel
          </Button>
        ) : null}

        {job.status === "completed" ||
        job.status === "failed" ||
        job.status === "cancelled" ? (
          <>
            <Button
              className={styles.secondaryButton}
              aria-label={
                (job.status === "failed" ? "Retry" : "Download again") +
                " " +
                job.episode_title
              }
              onPress={() => createMutation.mutate()}
              isDisabled={actionPending}
            >
              <Icon
                name={job.status === "failed" ? "refresh" : "download"}
                size={14}
              />
              {createMutation.isPending
                ? "Starting..."
                : job.status === "failed"
                  ? "Retry"
                  : "Download again"}
            </Button>
            <Button
              className={styles.dangerButton}
              aria-label={"Delete download record for " + job.episode_title}
              onPress={() => setConfirm("delete")}
              isDisabled={actionPending}
            >
              <Icon name="trash" size={14} />
              Delete record
            </Button>
          </>
        ) : null}
      </div>

      {confirm === "cancel" ? (
        <div
          className={styles.confirm}
          role="alertdialog"
          aria-label={"Cancel download for " + job.episode_title}
        >
          <p>Cancel this download and remove partial data?</p>
          <div className={styles.confirmActions}>
            <Button
              className={styles.secondaryButton}
              onPress={() => setConfirm(null)}
              isDisabled={cancelMutation.isPending}
            >
              Keep downloading
            </Button>
            <Button
              className={styles.dangerButton}
              aria-label="Cancel download"
              onPress={() => {
                setConfirm(null);
                cancelMutation.mutate(job.id);
              }}
              isDisabled={cancelMutation.isPending}
            >
              {cancelMutation.isPending ? "Cancelling..." : "Cancel download"}
            </Button>
          </div>
        </div>
      ) : null}

      {confirm === "delete" ? (
        <div
          className={styles.confirm}
          role="alertdialog"
          aria-label={"Delete download record for " + job.episode_title}
        >
          <p>Delete this download record? Downloaded files will be kept.</p>
          <div className={styles.confirmActions}>
            <Button
              className={styles.secondaryButton}
              onPress={() => setConfirm(null)}
              isDisabled={deleteMutation.isPending}
            >
              Keep record
            </Button>
            <Button
              className={styles.dangerButton}
              aria-label="Delete record"
              onPress={() => {
                setConfirm(null);
                deleteMutation.mutate(job.id);
              }}
              isDisabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete record"}
            </Button>
          </div>
        </div>
      ) : null}

      {pauseMutation.isError ? (
        <p className={styles.error} role="alert">
          {pauseMutation.error.message}
        </p>
      ) : null}
      {resumeMutation.isError ? (
        <p className={styles.error} role="alert">
          {resumeMutation.error.message}
        </p>
      ) : null}
      {cancelMutation.isError ? (
        <p className={styles.error} role="alert">
          {cancelMutation.error.message}
        </p>
      ) : null}
      {createMutation.isError ? (
        <p className={styles.error} role="alert">
          {createMutation.error.message}
        </p>
      ) : null}
      {deleteMutation.isError ? (
        <p className={styles.error} role="alert">
          {deleteMutation.error.message}
        </p>
      ) : null}
    </article>
  );
}

function StatusIcon({ status }: { status: DownloadJobListItem["status"] }) {
  switch (status) {
    case "completed":
      return <Icon name="checkCircle" size={16} />;
    case "failed":
      return <Icon name="alertCircle" size={16} />;
    case "paused":
      return <Icon name="pause" size={16} />;
    case "cancelled":
      return <Icon name="x" size={16} />;
    case "downloading":
      return <Icon name="download" size={16} />;
    case "pending":
      return <Icon name="clock" size={16} />;
  }
}

function getStatusLabel(status: DownloadJobListItem["status"]): string {
  switch (status) {
    case "pending":
      return "Queued";
    case "downloading":
      return "Downloading";
    case "paused":
      return "Paused";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    case "cancelled":
      return "Cancelled";
  }
}

function getProgress(job: DownloadJobListItem): {
  label: string;
  percent: number;
  width: string;
} {
  const label =
    job.total_bytes === null || job.total_bytes === 0
      ? formatBytes(job.downloaded_bytes)
      : formatBytes(job.downloaded_bytes) + " / " + formatBytes(job.total_bytes);
  const percent =
    job.total_bytes && job.total_bytes > 0
      ? Math.min(Math.round((job.downloaded_bytes / job.total_bytes) * 100), 100)
      : 0;
  return {
    label,
    percent,
    width: percent + "%",
  };
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
