import { Link, useParams } from "@tanstack/react-router";
import { ApiRequestError } from "../../../shared/api/client";
import { useAnimeDetail } from "../../../features/anime-detail/model/useAnimeDetail";
import styles from "./AnimeDetailPage.module.scss";

export default function AnimeDetailPage() {
  const { animeId } = useParams({ from: "/animes/$animeId" });
  const query = useAnimeDetail(animeId);

  if (query.isPending) {
    return (
      <main className={styles.page}>
        <p className={styles.state}>Loading anime...</p>
      </main>
    );
  }

  if (query.isError) {
    const isNotFound =
      query.error instanceof ApiRequestError && query.error.status === 404;

    return (
      <main className={styles.page}>
        <Link className={styles.backLink} to="/animes">
          ← Back to anime
        </Link>
        <section className={styles.state}>
          <h1>{isNotFound ? "Anime not found" : "Failed to load anime"}</h1>
          <p>
            {isNotFound
              ? "The requested anime no longer exists."
              : query.error instanceof Error
                ? query.error.message
                : "An unexpected error occurred."}
          </p>
        </section>
      </main>
    );
  }

  const { data: anime } = query;

  return (
    <main className={styles.page}>
      <Link className={styles.backLink} to="/animes">
        ← Back to anime
      </Link>

      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>Anime detail</p>
          <h1>{anime.title}</h1>
          <p className={styles.schedule}>
            {anime.year} · {formatLabel(anime.season)} ·{" "}
            {formatLabel(anime.weekday)} ·{" "}
            {anime.air_time ?? "Time not set"} ({anime.timezone})
          </p>
        </div>
        <span className={styles.episodeCount}>
          {anime.episodes.length} episodes
        </span>
      </header>

      <section className={styles.panel} aria-labelledby="episodes-heading">
        <div className={styles.panelHeader}>
          <div>
            <p className={styles.kicker}>Episodes</p>
            <h2 id="episodes-heading">Episode list</h2>
          </div>
        </div>

        {anime.episodes.length === 0 ? (
          <p className={styles.empty}>No episodes have been added yet.</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Episode</th>
                  <th scope="col">Title</th>
                  <th scope="col">Source</th>
                  <th scope="col">Size</th>
                  <th scope="col">Seeders</th>
                  <th scope="col">Leechers</th>
                  <th scope="col">Downloads</th>
                  <th scope="col">Download</th>
                  <th scope="col">Conversion</th>
                </tr>
              </thead>
              <tbody>
                {anime.episodes.map((episode) => (
                  <tr key={episode.id}>
                    <th scope="row">#{episode.episode_number}</th>
                    <td>{episode.title}</td>
                    <td>
                      {episode.source_url ? (
                        <a
                          href={episode.source_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {episode.source}
                        </a>
                      ) : (
                        episode.source
                      )}
                    </td>
                    <td>{episode.size ?? "Unknown"}</td>
                    <td>{formatCount(episode.seeders)}</td>
                    <td>{formatCount(episode.leechers)}</td>
                    <td>{formatCount(episode.downloads)}</td>
                    <td>
                      <span className={styles.status}>
                        {formatLabel(episode.download_status)}
                      </span>
                    </td>
                    <td>
                      <span className={styles.status}>
                        {formatLabel(episode.conversion_status)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

function formatLabel(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatCount(value: number | null): string {
  return value === null ? "—" : value.toLocaleString();
}
