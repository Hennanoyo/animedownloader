import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  Button,
  Menu,
  MenuItem,
  MenuTrigger,
  Popover,
} from "react-aria-components";
import type { Episode } from "../../../entities/anime/model/types";
import type {
  EpisodePipelineSummary,
  PipelineCurrentStage,
  PipelineStageStatus,
} from "../../../entities/anime/model/pipeline";
import {
  useCreateEpisodeDownloadJob,
  useDeleteDownloadJob,
  type DownloadJobSnapshot,
} from "../../../features/episode-download/model/useEpisodeDownload";
import EpisodeDownloadControl from "../../../features/episode-download/ui/EpisodeDownloadControl";
import { useDeleteEpisode } from "../../../features/episode-management/model/useEpisodeManagement";
import { useRetryEpisodePipeline } from "../../../features/anime-detail/model/useAnimePipeline";
import Icon from "../../../shared/ui/Icon";
import styles from "./EpisodePipelineCard.module.scss";

interface Props {
  episode: Episode;
  pipeline: EpisodePipelineSummary;
  realtimeConnected?: boolean;
}

const CONTINUE_ACTION_DELAY_MS = 1000;

const stages: { id: PipelineCurrentStage; label: string }[] = [
  { id: "download", label: "Download" },
  { id: "processing", label: "Processing" },
  { id: "preview", label: "Preview" },
  { id: "streaming", label: "Streaming" },
];

export default function EpisodePipelineCard({
  episode,
  pipeline,
  realtimeConnected = false,
}: Props) {
  const retryMutation = useRetryEpisodePipeline(episode.id);
  const deleteEpisodeMutation = useDeleteEpisode(episode.anime_id);
  const [expanded, setExpanded] = useState(
    pipeline.active || hasPipelineFailure(pipeline),
  );
  const [confirmAction, setConfirmAction] = useState<
    "delete-episode" | null
  >(null);
  const actionableStage = getActionableStage(pipeline);
  const continueActionStage = useDelayedContinueStage(
    actionableStage,
    pipeline,
  );
  const pipelineId = "episode-pipeline-" + episode.id;

  async function handleDeleteEpisode() {
    await deleteEpisodeMutation.mutateAsync(episode.id);
    setConfirmAction(null);
  }

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

        <EpisodeActionMenu
          episode={episode}
          download={pipeline.download}
          onDeleteEpisode={() => setConfirmAction("delete-episode")}
        />
      </div>

      <div className={styles.pipelineSection}>
        <Button
          className={styles.pipelineToggle}
          onPress={() => setExpanded((value) => !value)}
          aria-label={expanded ? "Hide details" : "Show details"}
          aria-expanded={expanded}
          aria-controls={pipelineId}
        >
          <span className={styles.pipelineSummaryLine}>
            {stages.map((stage) => (
              <span key={stage.id} className={styles.summaryStage}>
                <StageStatusIcon
                  status={getStageStatus(stage.id, pipeline)}
                  current={pipeline.current_stage === stage.id}
                />
                <span>{stage.label}</span>
              </span>
            ))}
          </span>
          <span className={styles.toggleLabel}>
            {expanded ? "Hide details" : "Show details"}
            <Icon
              className={styles.toggleIcon}
              name={expanded ? "chevronUp" : "chevronDown"}
              size={15}
            />
          </span>
        </Button>

        {expanded ? (
          <div
            id={pipelineId}
            className={styles.stages}
            aria-label="Media pipeline status"
          >
            {stages.map((stage) => {
              const stageStatus = getStageStatus(stage.id, pipeline);
              const completed = stageStatus === "completed";
              const current = pipeline.current_stage === stage.id;
              const action = getStageAction(
                stage.id,
                pipeline,
                continueActionStage,
              );

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
                        <StageStatusIcon
                          status={stageStatus}
                          current={current}
                        />
                        <span>{stage.label}</span>
                      </div>
                    </div>

                    {renderStageBody(
                      stage.id,
                      stageStatus,
                      pipeline,
                      realtimeConnected,
                    )}

                    {action ? (
                      <Button
                        className={styles.stageAction}
                        onPress={() => void retryMutation.mutateAsync()}
                        isDisabled={retryMutation.isPending}
                      >
                        <Icon
                          name={action === "Retry" ? "refresh" : "play"}
                          size={13}
                        />
                        <span>
                          {retryMutation.isPending ? "Starting..." : action}
                        </span>
                      </Button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        ) : null}
      </div>

      {confirmAction === "delete-episode" ? (
        <div
          className={styles.confirm}
          role="alertdialog"
          aria-label="Delete episode confirmation"
        >
          <div>
            <strong>Delete episode #{episode.episode_number}?</strong>
            <p>This removes the episode record. Downloaded media is kept.</p>
          </div>
          {deleteEpisodeMutation.isError ? (
            <p className={styles.error} role="alert">
              Failed to delete episode: {deleteEpisodeMutation.error.message}
            </p>
          ) : null}
          <div className={styles.confirmActions}>
            <Button
              className={styles.secondaryButton}
              onPress={() => setConfirmAction(null)}
              isDisabled={deleteEpisodeMutation.isPending}
            >
              Keep episode
            </Button>
            <Button
              className={styles.dangerButton}
              onPress={() => void handleDeleteEpisode()}
              isDisabled={deleteEpisodeMutation.isPending}
            >
              <Icon name="trash" size={14} />
              <span>
                {deleteEpisodeMutation.isPending ? "Deleting..." : "Delete episode"}
              </span>
            </Button>
          </div>
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

interface EpisodeActionMenuProps {
  episode: Episode;
  download: EpisodePipelineSummary["download"];
  onDeleteEpisode: () => void;
}

function EpisodeActionMenu({
  episode,
  download,
  onDeleteEpisode,
}: EpisodeActionMenuProps) {
  const createMutation = useCreateEpisodeDownloadJob(episode.id);
  const deleteMutation = useDeleteDownloadJob(episode.id);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const job = getDownloadJobSnapshot(download);
  const isDeleteDisabled =
    createMutation.isPending || deleteMutation.isPending;

  return (
    <div className={styles.actionMenu}>
      <MenuTrigger>
        <Button
          className={styles.iconButton}
          aria-label="Episode actions"
        >
          <Icon name="more" size={18} />
        </Button>
        <Popover
          className={styles.menuPopover}
          placement="bottom end"
          offset={6}
        >
          <Menu className={styles.menu} aria-label="Episode actions">
            <>
                {job?.status === "pending" ||
                job?.status === "downloading" ||
                job?.status === "paused" ? null : (
                  <MenuItem
                    className={styles.menuItem}
                    onAction={() => createMutation.mutate()}
                    isDisabled={createMutation.isPending}
                  >
                    <Icon
                      name={job?.status === "failed" ? "refresh" : "download"}
                      size={15}
                    />
                    <span>
                      {job?.status === "failed"
                        ? "Retry download"
                        : job?.status === "completed" ||
                            job?.status === "cancelled"
                          ? "Download again"
                          : "Download"}
                    </span>
                  </MenuItem>
                )}
                {job &&
                (job.status === "completed" ||
                  job.status === "failed" ||
                  job.status === "cancelled") ? (
                  <MenuItem
                    className={styles.menuItem}
                    onAction={() => setConfirmDelete(true)}
                    isDisabled={deleteMutation.isPending}
                  >
                    <Icon name="trash" size={15} />
                    <span>Delete download record</span>
                  </MenuItem>
                ) : null}
              </>
            <MenuItem
              className={styles.menuItem + " " + styles.menuItemDanger}
              onAction={onDeleteEpisode}
              isDisabled={isDeleteDisabled}
            >
              <Icon name="trash" size={15} />
              <span>Delete episode</span>
            </MenuItem>
          </Menu>
        </Popover>
      </MenuTrigger>

      {confirmDelete ? (
        <div className={styles.menuConfirm} role="alertdialog">
          <p>
            Delete this download record? Downloaded files will be kept.
          </p>
          <div className={styles.confirmActions}>
            <Button
              className={styles.secondaryButton}
              onPress={() => setConfirmDelete(false)}
              isDisabled={deleteMutation.isPending}
            >
              Keep record
            </Button>
            <Button
              className={styles.dangerButton}
              onPress={() => {
                if (job) {
                  deleteMutation.mutate(job.id);
                }
                setConfirmDelete(false);
              }}
              isDisabled={deleteMutation.isPending}
            >
              <Icon name="trash" size={14} />
              <span>
                {deleteMutation.isPending ? "Deleting..." : "Delete record"}
              </span>
            </Button>
          </div>
        </div>
      ) : null}

      {createMutation.isError ? (
        <span className={styles.menuError} role="alert">
          {createMutation.error instanceof Error
            ? createMutation.error.message
            : "Failed to start the download."}
        </span>
      ) : null}
      {deleteMutation.isError ? (
        <span className={styles.menuError} role="alert">
          {deleteMutation.error.message}
        </span>
      ) : null}
    </div>
  );
}

function getDownloadJobSnapshot(
  download: EpisodePipelineSummary["download"],
): DownloadJobSnapshot | null {
  if (!download.job_id) {
    return null;
  }

  switch (download.status) {
    case "pending":
    case "downloading":
    case "paused":
    case "completed":
    case "failed":
    case "cancelled":
      return {
        id: download.job_id,
        status: download.status,
        downloaded_bytes: download.downloaded_bytes,
        total_bytes: download.total_bytes,
        error_message: download.error_message,
      };
    default:
      return null;
  }
}

function StageStatusIcon({
  status,
  current,
}: {
  status: PipelineStageStatus;
  current: boolean;
}) {
  if (status === "completed") {
    return (
      <Icon className={styles.statusIconComplete} name="checkCircle" size={15} />
    );
  }

  if (status === "failed") {
    return (
      <Icon className={styles.statusIconFailed} name="alertCircle" size={15} />
    );
  }

  if (current || status === "processing" || status === "downloading" || status === "pending") {
    return (
      <span
        className={styles.statusIndicator}
        data-status={status}
        aria-label={status === "pending" ? "Waiting" : "In progress"}
      />
    );
  }

  return (
    <span
      className={styles.statusIndicator}
      data-status={status}
      aria-label="Not started"
    />
  );
}

function renderStageBody(
  stage: PipelineCurrentStage,
  stageStatus: PipelineStageStatus,
  pipeline: EpisodePipelineSummary,
  realtimeConnected: boolean,
) {
  if (stage === "download") {
    if (
      stageStatus === "pending" ||
      stageStatus === "downloading" ||
      stageStatus === "paused"
    ) {
      return (
        <EpisodeDownloadControl
          episodeId={pipeline.episode_id}
          inline
          realtimeConnected={realtimeConnected}
          jobSnapshot={getDownloadJobSnapshot(pipeline.download)}
        />
      );
    }

    if (stageStatus === "completed") {
      return (
        <OutputStatusList
          items={[
            {
              label: "File downloaded",
              detail: formatDownloadedBytes(
                pipeline.download.downloaded_bytes,
                pipeline.download.total_bytes,
              ),
              icon: "download",
            },
          ]}
        />
      );
    }

    if (pipeline.download.error_message) {
      return <p className={styles.error}>{pipeline.download.error_message}</p>;
    }

    if (stageStatus === "cancelled") {
      return <p className={styles.detail}>Download was cancelled.</p>;
    }

    return <p className={styles.detail}>Waiting to download.</p>;
  }

  if (stage === "processing") {
    if (
      stageStatus === "processing" ||
      (stageStatus === "pending" && pipeline.processing.progress_percent > 0)
    ) {
      return (
        <StageProgress
          label={
            pipeline.processing.progress_percent > 0
              ? "Preparation"
              : "Preparing"
          }
          value={pipeline.processing.progress_percent}
          indeterminate={pipeline.processing.progress_percent <= 0}
        />
      );
    }

    if (stageStatus === "completed") {
      return (
        <OutputStatusList
          items={[
            {
              label: pipeline.processing.playable_ready
                ? "Playable media ready"
                : "Playable media pending",
              icon: "play",
              complete: pipeline.processing.playable_ready,
            },
            {
              label: "Subtitles",
              icon: "caption",
              complete: pipeline.subtitles === "completed",
            },
            {
              label: "Attachments",
              icon: "paperclip",
              complete: pipeline.attachments === "completed",
            },
          ]}
        />
      );
    }

    if (pipeline.processing.error_message) {
      return <p className={styles.error}>{pipeline.processing.error_message}</p>;
    }

    return <p className={styles.detail}>Waiting for the downloaded file.</p>;
  }

  if (stage === "preview") {
    if (
      stageStatus === "processing" ||
      (stageStatus === "pending" && pipeline.thumbnail.progress_percent > 0)
    ) {
      return (
        <StageProgress
          label={
            pipeline.thumbnail.progress_percent > 0 ? "Sprite" : "Preparing"
          }
          value={pipeline.thumbnail.progress_percent}
          indeterminate={pipeline.thumbnail.progress_percent <= 0}
        />
      );
    }

    if (stageStatus === "completed") {
      return (
        <OutputStatusList
          items={[
            {
              label: "Sprite sheet ready",
              icon: "image",
              complete: Boolean(pipeline.thumbnail.url),
            },
            {
              label: "Thumbnail VTT ready",
              icon: "file",
              complete: Boolean(pipeline.thumbnail.vtt_url),
            },
          ]}
        />
      );
    }

    if (pipeline.thumbnail.error_message) {
      return <p className={styles.error}>{pipeline.thumbnail.error_message}</p>;
    }

    return <p className={styles.detail}>Waiting for playable media.</p>;
  }

  if (
    stageStatus === "processing" ||
    (stageStatus === "pending" && pipeline.streaming.progress_percent > 0)
  ) {
    return (
      <StageProgress
        label={
          pipeline.streaming.progress_percent > 0 ? "Packaging" : "Preparing"
        }
        value={pipeline.streaming.progress_percent}
        indeterminate={pipeline.streaming.progress_percent <= 0}
      />
    );
  }

  if (stageStatus === "completed") {
    return (
      <OutputStatusList
        items={[
          {
            label: "HLS ready",
            icon: "video",
            complete: pipeline.streaming.hls_ready,
          },
          {
            label: "DASH ready",
            icon: "video",
            complete: pipeline.streaming.dash_ready,
          },
        ]}
      />
    );
  }

  if (pipeline.streaming.error_message) {
    return <p className={styles.error}>{pipeline.streaming.error_message}</p>;
  }

  return <p className={styles.detail}>Waiting for the preview assets.</p>;
}

interface OutputStatus {
  label: string;
  icon:
    | "caption"
    | "download"
    | "file"
    | "paperclip"
    | "play"
    | "video"
    | "image";
  complete?: boolean;
  detail?: string;
}

function OutputStatusList({ items }: { items: OutputStatus[] }) {
  return (
    <div className={styles.outputList}>
      {items.map((item) => {
        const complete = item.complete ?? true;
        return (
          <span
            key={item.label}
            className={styles.outputItem}
            data-complete={complete}
          >
            <Icon
              name={item.icon}
              size={14}
              className={complete ? styles.outputIconReady : styles.outputIconPending}
            />
            <span>{item.label}</span>
            {item.detail ? <small>{item.detail}</small> : null}
          </span>
        );
      })}
    </div>
  );
}

interface StageProgressProps {
  label: string;
  value: number;
  indeterminate?: boolean;
}

function StageProgress({
  label,
  value,
  indeterminate = false,
}: StageProgressProps) {
  return (
    <div className={styles.progressBlock}>
      <div className={styles.progressMeta}>
        <span>{label}</span>
        <span>{indeterminate ? "…" : value + "%"}</span>
      </div>
      <div
        className={styles.progressTrack}
        data-indeterminate={indeterminate}
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        {...(indeterminate ? {} : { "aria-valuenow": value })}
      >
        <div
          className={styles.progressFill}
          style={{ width: indeterminate ? "35%" : value + "%" }}
        />
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
  continueActionStage: PipelineCurrentStage | null,
): "Continue" | "Retry" | null {
  const actionableStage = getActionableStage(pipeline);
  if (actionableStage === null || actionableStage !== stage) {
    return null;
  }

  const action = getBaseStageAction(stage, pipeline);
  if (action !== "Continue") {
    return action;
  }

  return continueActionStage === stage ? "Continue" : null;
}

function getBaseStageAction(
  stage: PipelineCurrentStage,
  pipeline: EpisodePipelineSummary,
): "Continue" | "Retry" | null {
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

function useDelayedContinueStage(
  actionableStage: PipelineCurrentStage | null,
  pipeline: EpisodePipelineSummary,
): PipelineCurrentStage | null {
  const pendingKey =
    actionableStage !== null &&
    getBaseStageAction(actionableStage, pipeline) === "Continue"
      ? getPendingActionKey(actionableStage, pipeline)
      : null;
  const [readyKey, setReadyKey] = useState<string | null>(null);

  useEffect(() => {
    if (pendingKey === null || actionableStage === null) {
      setReadyKey(null);
      return;
    }

    setReadyKey(null);
    const timeoutId = window.setTimeout(() => {
      setReadyKey(pendingKey);
    }, CONTINUE_ACTION_DELAY_MS);

    return () => window.clearTimeout(timeoutId);
  }, [actionableStage, pendingKey]);

  return readyKey === pendingKey && pendingKey !== null
    ? actionableStage
    : null;
}

function getPendingActionKey(
  stage: PipelineCurrentStage,
  pipeline: EpisodePipelineSummary,
): string {
  switch (stage) {
    case "processing":
      return [
        stage,
        pipeline.processing.status,
        pipeline.processing.job_id ?? "",
        pipeline.processing.preparation_job_id ?? "",
      ].join(":");
    case "preview":
      return [
        stage,
        pipeline.thumbnail.status,
        pipeline.processing.preparation_job_id ?? "",
      ].join(":");
    case "streaming":
      return [
        stage,
        pipeline.streaming.status,
        pipeline.streaming.job_id ?? "",
      ].join(":");
    case "download":
      return [
        stage,
        pipeline.download.status,
        pipeline.download.job_id ?? "",
      ].join(":");
  }
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

function formatDownloadedBytes(
  downloaded: number,
  total: number | null,
): string {
  const downloadedText = formatBytes(downloaded);
  return total ? downloadedText + " / " + formatBytes(total) : downloadedText;
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
