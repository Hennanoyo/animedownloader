import { Link, useSearch } from "@tanstack/react-router";
import DownloadJobCard from "../../../features/download-management/ui/DownloadJobCard";
import { Button } from "react-aria-components";
import {
  activeDownloadStatuses,
  failedDownloadStatuses,
  historyDownloadStatuses,
  terminalDownloadStatuses,
  useDownloadJobs,
} from "../../../features/download-management/model/useDownloadJobs";
import styles from "./DownloadManagerPage.module.scss";

const tabs = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "failed", label: "Failed" },
  { value: "history", label: "History" },
] as const;

export default function DownloadManagerPage() {
  const { status } = useSearch({ from: "/downloads" });

  const activeQuery = useDownloadJobs({
    statuses: [...activeDownloadStatuses],
    enabled: status === "all" || status === "active",
  });
  const terminalQuery = useDownloadJobs({
    statuses: [...terminalDownloadStatuses],
    enabled: status === "all",
  });
  const failedQuery = useDownloadJobs({
    statuses: [...failedDownloadStatuses],
    enabled: status === "failed",
  });
  const historyQuery = useDownloadJobs({
    statuses: [...historyDownloadStatuses],
    enabled: status === "history",
  });

  const query =
    status === "active"
      ? activeQuery
      : status === "failed"
        ? failedQuery
        : status === "history"
          ? historyQuery
          : null;

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>Download manager</p>
          <h1>Downloads</h1>
          <p>Monitor and control current and recent episode downloads.</p>
        </div>
      </header>

      <nav className={styles.tabs} aria-label="Download filters">
        {tabs.map((tab) => (
          <Link
            key={tab.value}
            className={styles.tab}
            activeProps={{ className: styles.tabActive }}
            to="/downloads"
            search={{ status: tab.value }}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      {status === "all" ? (
        <div className={styles.sections}>
          <DownloadSection
            title="Active"
            query={activeQuery}
            emptyMessage="No downloads are currently active."
          />
          <DownloadSection
            title="Recent history"
            query={terminalQuery}
            emptyMessage="No completed, failed, or cancelled downloads yet."
          />
        </div>
      ) : query ? (
        <div className={styles.sections}>
          <DownloadSection
            title={tabs.find((tab) => tab.value === status)?.label ?? "Downloads"}
            query={query}
            emptyMessage={getEmptyMessage(status)}
          />
        </div>
      ) : null}
    </main>
  );
}

function DownloadSection({
  title,
  query,
  emptyMessage,
}: {
  title: string;
  query: ReturnType<typeof useDownloadJobs>;
  emptyMessage: string;
}) {
  const headingId = "download-section-" + title.toLowerCase().replaceAll(" ", "-");

  if (query.isPending) {
    return (
      <section className={styles.section}>
        <h2 id={headingId}>{title}</h2>
        <p className={styles.state}>Loading downloads...</p>
      </section>
    );
  }

  if (query.isError) {
    return (
      <section className={styles.section} aria-labelledby={headingId}>
        <h2 id={headingId}>{title}</h2>
        <p className={styles.error} role="alert">
          Failed to load downloads: {query.error.message}
        </p>
        <Button
          className={styles.retryButton}
          onPress={() => void query.refetch()}
        >
          Retry
        </Button>
      </section>
    );
  }

  return (
    <section className={styles.section} aria-labelledby={headingId}>
      <div className={styles.sectionHeader}>
        <h2 id={headingId}>{title}</h2>
        <span>{query.data.total} total</span>
      </div>
      {query.data.items.length === 0 ? (
        <p className={styles.state}>{emptyMessage}</p>
      ) : (
        <div className={styles.list}>
          {query.data.items.map((job) => (
            <DownloadJobCard key={job.id} job={job} />
          ))}
        </div>
      )}
    </section>
  );
}

function getEmptyMessage(
  status: "active" | "failed" | "history",
): string {
  switch (status) {
    case "active":
      return "No downloads are currently active.";
    case "failed":
      return "No failed downloads.";
    case "history":
      return "No completed or cancelled downloads yet.";
  }
}
