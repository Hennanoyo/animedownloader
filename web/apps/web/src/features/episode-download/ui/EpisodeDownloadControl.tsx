import { Button } from "react-aria-components";
import { ApiRequestError } from "../../../shared/api/client";
import {
  useCreateEpisodeDownloadJob,
  useEpisodeDownload,
} from "../model/useEpisodeDownload";
import styles from "./EpisodeDownloadControl.module.scss";

interface Props {
  episodeId: string;
}

export default function EpisodeDownloadControl({ episodeId }: Props) {
  const query = useEpisodeDownload(episodeId);
  const mutation = useCreateEpisodeDownloadJob(episodeId);

  if (query.isPending) {
    return <span className={styles.message}>Checking...</span>;
  }

  if (query.isError) {
    return (
      <div className={styles.control}>
        <span className={styles.error}>Failed to load download status.</span>
        <Button
          className={styles.secondaryButton}
          onPress={() => void query.refetch()}
        >
          Retry
        </Button>
      </div>
    );
  }

  const job = query.data;

  if (job?.status === "pending" || job?.status === "downloading") {
    return (
      <div className={styles.control}>
        <span className={styles.status}>
          {job.status === "pending" ? "Queued" : "Downloading"}
        </span>
        <div className={styles.progressTrack}>
          <div
            className={styles.progress}
            style={{
              width:
                job.total_bytes && job.total_bytes > 0
                  ? `${Math.min(
                      (job.downloaded_bytes / job.total_bytes) * 100,
                      100,
                    )}%`
                  : "0%",
            }}
          />
        </div>
        <span className={styles.progressLabel}>{formatProgress(job)}</span>
      </div>
    );
  }

  if (job?.status === "completed") {
    return (
      <div className={styles.control}>
        <span className={styles.completed}>Completed</span>
        <span className={styles.progressLabel}>{formatProgress(job)}</span>
        <Button
          className={styles.secondaryButton}
          onPress={() => mutation.mutate()}
          isDisabled={mutation.isPending}
        >
          {mutation.isPending ? "Starting..." : "Redownload"}
        </Button>
      </div>
    );
  }

  if (job?.status === "failed") {
    return (
      <div className={styles.control}>
        <span className={styles.error}>Failed</span>
        {job.error_message ? (
          <span className={styles.errorDetail}>{job.error_message}</span>
        ) : null}
        <Button
          className={styles.secondaryButton}
          onPress={() => mutation.mutate()}
          isDisabled={mutation.isPending}
        >
          {mutation.isPending ? "Retrying..." : "Retry"}
        </Button>
      </div>
    );
  }

  if (job?.status === "cancelled") {
    return (
      <div className={styles.control}>
        <span className={styles.message}>Cancelled</span>
        <Button
          className={styles.secondaryButton}
          onPress={() => mutation.mutate()}
          isDisabled={mutation.isPending}
        >
          {mutation.isPending ? "Starting..." : "Download again"}
        </Button>
      </div>
    );
  }

  return (
    <div className={styles.control}>
      <Button
        className={styles.primaryButton}
        onPress={() => mutation.mutate()}
        isDisabled={mutation.isPending}
      >
        {mutation.isPending ? "Starting..." : "Download"}
      </Button>
      {mutation.isError ? (
        <span className={styles.error}>
          {mutation.error instanceof ApiRequestError
            ? mutation.error.message
            : "Failed to start download."}
        </span>
      ) : null}
    </div>
  );
}

function formatProgress(job: {
  downloaded_bytes: number;
  total_bytes: number | null;
}): string {
  const downloaded = formatBytes(job.downloaded_bytes);

  if (job.total_bytes === null || job.total_bytes === 0) {
    return downloaded;
  }

  return downloaded + " / " + formatBytes(job.total_bytes);
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
