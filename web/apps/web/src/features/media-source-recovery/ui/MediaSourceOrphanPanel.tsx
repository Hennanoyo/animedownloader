import { useState } from "react";
import { Button } from "react-aria-components";
import {
  useDeleteMediaSourceOrphan,
  useMediaSourceOrphans,
} from "../model/useMediaSource";
import styles from "./MediaSourceOrphanPanel.module.scss";

export default function MediaSourceOrphanPanel() {
  const [open, setOpen] = useState(false);
  const query = useMediaSourceOrphans(open);
  const deleteMutation = useDeleteMediaSourceOrphan();

  return (
    <section className={styles.panel} aria-labelledby="orphan-heading">
      <div className={styles.header}>
        <div>
          <p className={styles.kicker}>Source maintenance</p>
          <h2 id="orphan-heading">Orphaned download sources</h2>
          <p>
            These directories are not associated with a current DownloadJob.
            They are not deleted automatically.
          </p>
        </div>
        <Button
          className={styles.secondaryButton}
          onPress={() => setOpen((value) => !value)}
        >
          {open ? "Hide" : "Review"}
        </Button>
      </div>

      {open ? (
        <>
          {query.isPending ? (
            <p className={styles.state}>Scanning download sources…</p>
          ) : null}

          {query.isError ? (
            <div className={styles.errorBlock} role="alert">
              <p>Failed to scan orphaned sources.</p>
              <p>{query.error.message}</p>
              <Button
                className={styles.secondaryButton}
                onPress={() => void query.refetch()}
              >
                Retry
              </Button>
            </div>
          ) : null}

          {query.data ? (
            query.data.length === 0 ? (
              <p className={styles.state}>No orphaned download sources found.</p>
            ) : (
              <div className={styles.list}>
                {query.data.map((orphan) => (
                  <OrphanRow
                    key={orphan.directory_id}
                    directoryId={orphan.directory_id}
                    path={orphan.path}
                    disabled={deleteMutation.isPending}
                    onDelete={() => deleteMutation.mutate(orphan.directory_id)}
                  />
                ))}
              </div>
            )
          ) : null}

          {deleteMutation.isError ? (
            <p className={styles.error} role="alert">
              {deleteMutation.error.message}
            </p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function OrphanRow({
  directoryId,
  path,
  disabled,
  onDelete,
}: {
  directoryId: string;
  path: string;
  disabled: boolean;
  onDelete: () => void;
}) {
  const [confirm, setConfirm] = useState(false);

  if (confirm) {
    return (
      <div className={styles.confirm}>
        <div>
          <strong>Delete this source directory?</strong>
          <p>{path}</p>
        </div>
        <div className={styles.actions}>
          <Button
            className={styles.secondaryButton}
            onPress={() => setConfirm(false)}
            isDisabled={disabled}
          >
            Keep
          </Button>
          <Button
            className={styles.dangerButton}
            onPress={() => {
              onDelete();
              setConfirm(false);
            }}
            isDisabled={disabled}
          >
            Delete source
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.row}>
      <code>{path}</code>
      <Button
        className={styles.dangerButton}
        onPress={() => setConfirm(true)}
        isDisabled={disabled}
        aria-label={"Delete " + directoryId}
      >
        Delete
      </Button>
    </div>
  );
}
