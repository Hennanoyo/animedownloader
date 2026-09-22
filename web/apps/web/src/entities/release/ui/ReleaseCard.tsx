import type { Release } from "../model/types";
import styles from "./ReleaseCard.module.scss";

interface ReleaseCardProps {
  release: Release;
}

function formatDate(value: Date | null): string {
  if (!value) {
    return "Unknown date";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(value);
}

export default function ReleaseCard({ release }: ReleaseCardProps) {
  return (
    <article className={styles.card}>
      <h2 className={styles.title}>{release.title}</h2>
      <div className={styles.meta}>
        <span>{formatDate(release.published_at)}</span>
        <span>{release.size ?? "Unknown size"}</span>
        <span>Seeders {release.seeders ?? 0}</span>
        <span>Leechers {release.leechers ?? 0}</span>
        <span>Downloads {release.downloads ?? 0}</span>
      </div>
      {release.info_hash ? (
        <p className={styles.hash}>Info hash: {release.info_hash}</p>
      ) : null}
      <div className={styles.actions}>
        <a
          className={styles.link}
          href={release.page_url}
          target="_blank"
          rel="noreferrer"
        >
          View release
        </a>
        <a
          className={styles.link}
          href={release.torrent_url}
          target="_blank"
          rel="noreferrer"
        >
          Torrent
        </a>
      </div>
    </article>
  );
}
