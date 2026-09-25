import { useState } from "react";
import { Button } from "react-aria-components";
import { ApiRequestError } from "../../../shared/api/client";
import Icon from "../../../shared/ui/Icon";
import {
  useCancelDownloadJob,
  useCreateEpisodeDownloadJob,
  useDeleteDownloadJob,
  useEpisodeDownload,
  usePauseDownloadJob,
  useResumeDownloadJob,
} from "../model/useEpisodeDownload";
import type { DownloadJob } from "../../../entities/download/model/types";
import styles from "./EpisodeDownloadControl.module.scss";

type DownloadJobSnapshot = Pick<
  DownloadJob,
  "id" | "status" | "downloaded_bytes" | "total_bytes" | "error_message"
>;

interface Props {
  episodeId: string;
  compact?: boolean;
  inline?: boolean;
  realtimeConnected?: boolean;
  job?: DownloadJobSnapshot;
}

export default function EpisodeDownloadControl({
  episodeId,
  compact = false,
  inline = false,
  realtimeConnected = false,
  job: jobSnapshot,
}: Props) {
  const query = useEpisodeDownload(
    episodeId,
    realtimeConnected,
    jobSnapshot === undefined,
  );
  const createMutation = useCreateEpisodeDownloadJob(episodeId);
  const pauseMutation = usePauseDownloadJob(episodeId);
  const resumeMutation = useResumeDownloadJob(episodeId);
  const cancelMutation = useCancelDownloadJob(episodeId);
  const deleteMutation = useDeleteDownloadJob(episodeId);
  const [confirm, setConfirm] = useState<"cancel" | "delete" | null>(null);

  const job: DownloadJobSnapshot | null | undefined =
    jobSnapshot ?? query.data;

  if (
    jobSnapshot === undefined &&
    (job === undefined || job === null) &&
    query.isPending
  ) {
    return <span className={styles.message}>Checking...</span>;
  }

  if (
    jobSnapshot === undefined &&
    (job === undefined || job === null) &&
    query.isError
  ) {
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

  if (job?.status === "pending" || job?.status === "downloading") {
    const pending = pauseMutation.isPending || cancelMutation.isPending;

    if (inline) {
      return (
        <InlineDownloadState
          job={job}
          statusLabel={job.status === "pending" ? "Queued" : "Downloading"}
          pending={pending}
          isPausing={pauseMutation.isPending}
          isCancelling={cancelMutation.isPending}
          onPause={() => pauseMutation.mutate(job.id)}
          onCancel={() => setConfirm("cancel")}
          confirm={confirm}
          onKeep={() => setConfirm(null)}
          onConfirmCancel={() => {
            setConfirm(null);
            cancelMutation.mutate(job.id);
          }}
          cancelError={cancelMutation.isError ? cancelMutation.error.message : null}
          pauseError={pauseMutation.isError ? pauseMutation.error.message : null}
        />
      );
    }

    return (
      <div
        className={compact ? styles.control + " " + styles.compact : styles.control}
        data-compact={compact || undefined}
      >
        {compact ? null : (
          <>
            <span className={styles.status}>
              {job.status === "pending" ? "Queued" : "Downloading"}
            </span>
            <div className={styles.progressTrack}>
              <div
                className={styles.progress}
                style={{
                  width:
                    job.total_bytes && job.total_bytes > 0
                      ? Math.min(
                          (job.downloaded_bytes / job.total_bytes) * 100,
                          100,
                        ) + "%"
                      : "0%",
                }}
              />
            </div>
            <span className={styles.progressLabel}>
              {formatProgress(job)}
            </span>
          </>
        )}
        {confirm === "cancel" ? (
          <div className={styles.confirm} role="alertdialog">
            <span>Cancel this download and remove partial data?</span>
            <div className={styles.buttons}>
              <Button
                className={styles.secondaryButton}
                onPress={() => setConfirm(null)}
                isDisabled={cancelMutation.isPending}
              >
                Keep downloading
              </Button>
              <Button
                className={styles.dangerButton}
                onPress={() => {
                  setConfirm(null);
                  cancelMutation.mutate(job.id);
                }}
                isDisabled={pending}
              >
                {cancelMutation.isPending ? "Cancelling..." : "Cancel download"}
              </Button>
            </div>
          </div>
        ) : (
          <div className={styles.buttons}>
            <Button
              className={styles.secondaryButton}
              onPress={() => pauseMutation.mutate(job.id)}
              isDisabled={pending}
            >
              {pauseMutation.isPending ? "Pausing..." : "Pause"}
            </Button>
            <Button
              className={styles.dangerButton}
              onPress={() => setConfirm("cancel")}
              isDisabled={pending}
            >
              Cancel
            </Button>
          </div>
        )}
        {pauseMutation.isError ? (
          <span className={styles.error}>{pauseMutation.error.message}</span>
        ) : null}
        {cancelMutation.isError ? (
          <span className={styles.error}>{cancelMutation.error.message}</span>
        ) : null}
      </div>
    );
  }

  if (job?.status === "paused") {
    const pending = resumeMutation.isPending || cancelMutation.isPending;

    if (inline) {
      return (
        <InlineDownloadState
          job={job}
          statusLabel="Paused"
          pending={pending}
          isPausing={false}
          isCancelling={cancelMutation.isPending}
          onPause={() => resumeMutation.mutate(job.id)}
          onCancel={() => setConfirm("cancel")}
          confirm={confirm}
          onKeep={() => setConfirm(null)}
          onConfirmCancel={() => {
            setConfirm(null);
            cancelMutation.mutate(job.id);
          }}
          cancelError={cancelMutation.isError ? cancelMutation.error.message : null}
          pauseError={resumeMutation.isError ? resumeMutation.error.message : null}
          paused
        />
      );
    }

    return (
      <div
        className={compact ? styles.control + " " + styles.compact : styles.control}
        data-compact={compact || undefined}
      >
        {compact ? null : (
          <>
            <span className={styles.status}>Paused</span>
            <span className={styles.progressLabel}>{formatProgress(job)}</span>
          </>
        )}
        {confirm === "cancel" ? (
          <div className={styles.confirm} role="alertdialog">
            <span>Cancel this download and remove partial data?</span>
            <div className={styles.buttons}>
              <Button
                className={styles.secondaryButton}
                onPress={() => setConfirm(null)}
                isDisabled={pending}
              >
                Keep paused
              </Button>
              <Button
                className={styles.dangerButton}
                onPress={() => {
                  setConfirm(null);
                  cancelMutation.mutate(job.id);
                }}
                isDisabled={pending}
              >
                {cancelMutation.isPending ? "Cancelling..." : "Cancel download"}
              </Button>
            </div>
          </div>
        ) : (
          <div className={styles.buttons}>
            <Button
              className={styles.primaryButton}
              onPress={() => resumeMutation.mutate(job.id)}
              isDisabled={pending}
            >
              {resumeMutation.isPending ? "Resuming..." : "Resume"}
            </Button>
            <Button
              className={styles.dangerButton}
              onPress={() => setConfirm("cancel")}
              isDisabled={pending}
            >
              Cancel
            </Button>
          </div>
        )}
        {resumeMutation.isError ? (
          <span className={styles.error}>{resumeMutation.error.message}</span>
        ) : null}
        {cancelMutation.isError ? (
          <span className={styles.error}>{cancelMutation.error.message}</span>
        ) : null}
      </div>
    );
  }

  if (job?.status === "completed") {
    return (
      <TerminalDownloadControl
        compact={compact}
        job={job}
        onDownload={() => createMutation.mutate()}
        onDelete={() => setConfirm("delete")}
        deleteMutation={deleteMutation}
        createMutation={createMutation}
        confirm={confirm}
        onCancelConfirm={() => setConfirm(null)}
      />
    );
  }

  if (job?.status === "failed") {
    return (
      <TerminalDownloadControl
        compact={compact}
        job={job}
        onDownload={() => createMutation.mutate()}
        onDelete={() => setConfirm("delete")}
        deleteMutation={deleteMutation}
        createMutation={createMutation}
        confirm={confirm}
        onCancelConfirm={() => setConfirm(null)}
        showError
      />
    );
  }

  if (job?.status === "cancelled") {
    return (
      <TerminalDownloadControl
        compact={compact}
        job={job}
        onDownload={() => createMutation.mutate()}
        onDelete={() => setConfirm("delete")}
        deleteMutation={deleteMutation}
        createMutation={createMutation}
        confirm={confirm}
        onCancelConfirm={() => setConfirm(null)}
      />
    );
  }

  return (
    <div className={styles.control}>
      <Button
        className={styles.primaryButton}
        onPress={() => createMutation.mutate()}
        isDisabled={createMutation.isPending}
      >
        {createMutation.isPending ? "Starting..." : "Download"}
      </Button>
      {createMutation.isError ? (
        <span className={styles.error}>
          {createMutation.error instanceof ApiRequestError
            ? createMutation.error.message
            : "Failed to start download."}
        </span>
      ) : null}
    </div>
  );
}

interface InlineDownloadStateProps {
  job: DownloadJobSnapshot;
  statusLabel: string;
  pending: boolean;
  isPausing: boolean;
  isCancelling: boolean;
  onPause: () => void;
  onCancel: () => void;
  confirm: "cancel" | "delete" | null;
  onKeep: () => void;
  onConfirmCancel: () => void;
  cancelError: string | null;
  pauseError: string | null;
  paused?: boolean;
}

function InlineDownloadState({
  job,
  statusLabel,
  pending,
  isPausing,
  isCancelling,
  onPause,
  onCancel,
  confirm,
  onKeep,
  onConfirmCancel,
  cancelError,
  pauseError,
  paused = false,
}: InlineDownloadStateProps) {
  return (
    <div className={styles.inlineControl} data-inline="true" aria-label="Download progress">
      <div className={styles.inlineMeta}>
        <span className={styles.status}>{statusLabel}</span>
        <span className={styles.progressLabel}>{formatProgress(job)}</span>
      </div>
      {paused ? null : (
        <div className={styles.progressTrack}>
          <div
            className={styles.progress}
            style={{
              width:
                job.total_bytes && job.total_bytes > 0
                  ? Math.min(
                      (job.downloaded_bytes / job.total_bytes) * 100,
                      100,
                    ) + "%"
                  : "0%",
            }}
          />
        </div>
      )}

      {confirm === "cancel" ? (
        <div className={styles.inlineConfirm} role="alertdialog">
          <span>Cancel this download and remove partial data?</span>
          <div className={styles.buttons}>
            <Button
              className={styles.secondaryButton}
              onPress={onKeep}
              isDisabled={pending}
            >
              Keep
            </Button>
            <Button
              className={styles.dangerButton}
              onPress={onConfirmCancel}
              isDisabled={pending}
            >
              {isCancelling ? "Cancelling..." : "Cancel download"}
            </Button>
          </div>
        </div>
      ) : (
        <div className={styles.iconButtons}>
          <Button
            className={styles.iconButton}
            aria-label={paused ? "Resume download" : "Pause download"}
            onPress={onPause}
            isDisabled={pending}
          >
            <Icon name={paused ? "play" : "pause"} size={15} />
            {isPausing ? (
              <span className={styles.srOnly}>Starting...</span>
            ) : null}
          </Button>
          <Button
            className={styles.iconButtonDanger}
            aria-label="Cancel download"
              onPress={onCancel}
            isDisabled={pending}
          >
            <Icon name="x" size={15} />
          </Button>
        </div>
      )}

      {pauseError ? <span className={styles.error}>{pauseError}</span> : null}
      {cancelError ? <span className={styles.error}>{cancelError}</span> : null}
    </div>
  );
}

interface TerminalDownloadControlProps {
  compact?: boolean;
  job: DownloadJobSnapshot;
  onDownload: () => void;
  onDelete: () => void;
  deleteMutation: ReturnType<typeof useDeleteDownloadJob>;
  createMutation: ReturnType<typeof useCreateEpisodeDownloadJob>;
  confirm: "cancel" | "delete" | null;
  onCancelConfirm: () => void;
  showError?: boolean;
}

function TerminalDownloadControl({
  compact = false,
  job,
  onDownload,
  onDelete,
  deleteMutation,
  createMutation,
  confirm,
  onCancelConfirm,
  showError = false,
}: TerminalDownloadControlProps) {
  return (
    <div
      className={compact ? styles.control + " " + styles.compact : styles.control}
      data-compact={compact || undefined}
    >
      {compact ? null : (
        <span className={job.status === "failed" ? styles.error : styles.message}>
          {job.status === "completed"
            ? "Completed"
            : job.status === "failed"
              ? "Failed"
              : "Cancelled"}
        </span>
      )}
      {job.status === "failed" && job.error_message ? (
        <span className={styles.errorDetail}>{job.error_message}</span>
      ) : null}
      {compact ? null : (
        <span className={styles.progressLabel}>{formatProgress(job)}</span>
      )}
      <div className={styles.buttons}>
        <Button
          className={styles.secondaryButton}
          onPress={onDownload}
          isDisabled={createMutation.isPending || deleteMutation.isPending}
        >
          {createMutation.isPending ? "Starting..." : job.status === "failed" ? "Retry" : "Download again"}
        </Button>
        <Button
          className={styles.dangerButton}
          onPress={onDelete}
          isDisabled={createMutation.isPending || deleteMutation.isPending}
        >
          Delete record
        </Button>
      </div>
      {confirm === "delete" ? (
        <div className={styles.confirm} role="alertdialog">
          <span>
            {showError
              ? "Delete this failed download record? Its partial files will be kept."
              : "Delete this download record? Downloaded files will be kept."}
          </span>
          <div className={styles.buttons}>
            <Button
              className={styles.secondaryButton}
              onPress={onCancelConfirm}
              isDisabled={deleteMutation.isPending}
            >
              Keep record
            </Button>
            <Button
              className={styles.dangerButton}
              onPress={() => {
                onCancelConfirm();
                deleteMutation.mutate(job.id);
              }}
              isDisabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete record"}
            </Button>
          </div>
        </div>
      ) : null}
      {deleteMutation.isError ? (
        <span className={styles.error}>{deleteMutation.error.message}</span>
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
