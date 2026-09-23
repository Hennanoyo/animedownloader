import { Link } from "@tanstack/react-router";
import { useAnimes } from "../../../features/anime-create/model/useCreateAnime";
import styles from "./AnimeListPage.module.scss";

export default function AnimeListPage() {
  const query = useAnimes();

  return (
    <main className={styles.page}>
      <div className={styles.header}>
        <div>
          <p className={styles.kicker}>Catalog</p>
          <h1>Anime</h1>
          <p>Anime records stored in PostgreSQL.</p>
        </div>
        <Link className={styles.primaryButton} to="/animes/new">
          Add anime
        </Link>
      </div>

      {query.isPending ? <p className={styles.state}>Loading anime...</p> : null}
      {query.isError ? (
        <p className={[styles.state, styles.error].join(" ")}>
          Failed to load anime: {query.error.message}
        </p>
      ) : null}
      {query.isSuccess && query.data.length === 0 ? (
        <p className={styles.state}>No anime have been created yet.</p>
      ) : null}

      <div className={styles.list}>
        {query.data?.map((anime) => (
          <article className={styles.card} key={anime.id}>
            <div className={styles.cardHeader}>
              <div>
                <h2>
                  <Link
                    className={styles.titleLink}
                    to="/animes/$animeId"
                    params={{ animeId: anime.id }}
                  >
                    {anime.title}
                  </Link>
                </h2>
                <p>
                  {anime.year} · {anime.season} · {anime.weekday} ·{" "}
                  {anime.air_time ?? "time not set"} ({anime.timezone})
                </p>
              </div>
              <Link
                className={styles.detailLink}
                to="/animes/$animeId"
                params={{ animeId: anime.id }}
              >
                {anime.episodes.length} episodes · View details
              </Link>
            </div>

            <div className={styles.episodes}>
              {anime.episodes.map((episode) => (
                <div className={styles.episode} key={episode.id}>
                  <strong>
                    #{episode.episode_number} {episode.title}
                  </strong>
                  <span>{episode.size ?? "Unknown size"}</span>
                  <span>
                    Download: {episode.download_status.replace("_", " ")} ·
                    Conversion: {episode.conversion_status.replace("_", " ")}
                  </span>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
