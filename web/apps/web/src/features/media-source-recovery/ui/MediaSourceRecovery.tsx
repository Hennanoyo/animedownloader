import { useState } from "react";
import { Button } from "react-aria-components";
import {
  useEpisodeMediaSource,
  useReprocessEpisodeMediaSource,
  useRedownloadEpisodeMediaSource,
  useSelectEpisodeMediaSource,
} from "../model/useMediaSource";
import styles from "./MediaSourceRecovery.module.scss";

interface Props {
  episodeId: string;
}

export default function MediaSourceRecovery({ episodeId }: Props) {
  const [open, setOpen] = useState(false);
  const query = useEpisodeMediaSource(episodeId, open);
  const reprocess = useReprocessEpisodeMediaSource(episodeId);
  const redownload = useRedownloadEpisodeMediaSource(episodeId);
  const select = useSelectEpisodeMediaSource(episodeId);

  if (!open) {
    return (
      <Button className={styles.reviewButton} onPress={() => setOpen(true)}>
        Review source
      </Button>
    );
  }

  const source = query.data;
  const busy =
    reprocess.isPending || redownload.isPending || select.isPending;

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div>
          <strong>Downloaded source</strong>
          <p>Inspect or recover the local source without touching derived media.</p>
        </div>
        <Button
          className={styles.secondaryButton}
          onPress={() => setOpen(false)}
        >
          Hide
        </Button>
      </div>

      {query.isPending ? <p className={styles.detail}>Scanning source…</p> : null}

      {query.isError ? (
        <div className={styles.errorBlock} role="alert">
          <p>Failed to inspect the source.</p>
          <p>{query.error instanceof Error ? query.error.message : "Unknown error."}</p>
          <Button
            className={styles.secondaryButton}
            onPress={() => void query.refetch()}
          >
            Retry
          </Button>
        </div>
      ) : null}

      {source ? (
        <>
          <div className={styles.statusRow}>
            <span>Status</span>
            <strong data-status={source.status}>{formatStatus(source.status)}</strong>
          </div>

          {source.status === "found" ? (
            <>
              <p className={styles.detail}>
                {source.selected_path
                  ? "Selected source: " + source.selected_path
                  : "Exactly one supported media file was found."}
              </p>
              <div className={styles.actions}>
                <Button
                  className={styles.primaryButton}
                  onPress={() => void reprocess.mutateAsync()}
                  isDisabled={busy || source.processing_status === "completed"}
                >
                  {reprocess.isPending ? "Starting…" : "Process source"}
                </Button>
              </div>
            </>
          ) : null}

          {source.status === "ambiguous" ? (
            <div className={styles.candidates}>
              <p className={styles.detail}>
                Multiple media files were found. Select exactly one before processing.
              </p>
              {source.candidates.map((candidate) => (
                <div className={styles.candidate} key={candidate.path}>
                  <code>{candidate.path}</code>
                  <Button
                    className={styles.secondaryButton}
                    onPress={() => void select.mutateAsync(candidate.path)}
                    isDisabled={busy || source.processing_status === "completed"}
                  >
                    {source.selected_path === candidate.path
                      ? "Selected"
                      : "Use source"}
                  </Button>
                </div>
              ))}
            </div>
          ) : null}

          {source.status === "missing_directory" || source.status === "no_media" ? (
            <div className={styles.warningBlock}>
              <p>
                The completed download no longer has a usable source directory.
              </p>
              <Button
                className={styles.primaryButton}
                onPress={() => void redownload.mutateAsync()}
                isDisabled={busy}
              >
                {redownload.isPending ? "Starting…" : "Download again"}
              </Button>
            </div>
          ) : null}

          {source.status === "not_available" ? (
            <p className={styles.detail}>
              No completed download is available for this episode.
            </p>
          ) : null}

          {source.processing_status === "processing" ? (
            <p className={styles.detail}>Media processing is already running.</p>
          ) : null}

          {source.processing_status === "completed" ? (
            <p className={styles.detail}>Media processing is complete for this source.</p>
          ) : null}

          {reprocess.isError || redownload.isError || select.isError ? (
            <p className={styles.error} role="alert">
              {(reprocess.error ?? redownload.error ?? select.error) instanceof Error
                ? (reprocess.error ?? redownload.error ?? select.error)?.message
                : "Source recovery failed."}
            </p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function formatStatus(status: string): string {
  return status.replaceAll("_", " ");
}
