import { Link, useParams } from "@tanstack/react-router";
import { Button } from "react-aria-components";
import { usePlayback } from "../../../features/playback/model/usePlayback";
import { ApiRequestError } from "../../../shared/api/client";
import VideoPlayer from "../../../widgets/video-player/ui/VideoPlayer";
import styles from "./EpisodePlayerPage.module.scss";

export default function EpisodePlayerPage() {
  const { episodeId } = useParams({ from: "/episodes/$episodeId" });
  const query = usePlayback(episodeId);

  if (query.isPending) {
    return (
      <main className={styles.page}>
        <p className={styles.state}>Loading playback...</p>
      </main>
    );
  }

  if (query.isError) {
    const message =
      query.error instanceof ApiRequestError && query.error.status === 404
        ? "The requested episode no longer exists."
        : query.error instanceof Error
          ? query.error.message
          : "An unexpected error occurred.";

    return (
      <main className={styles.page}>
        <Link className={styles.backLink} to="/animes">
          ← Back to anime
        </Link>
        <section className={styles.state}>
          <h1>Unable to load playback</h1>
          <p className={styles.error}>{message}</p>
          <Button
            className={styles.retryButton}
            isDisabled={query.isFetching}
            onPress={() => {
              void query.refetch();
            }}
          >
            {query.isFetching ? "Retrying..." : "Retry"}
          </Button>
        </section>
      </main>
    );
  }

  const playback = query.data;

  return (
    <main className={styles.page}>
      <Link
        className={styles.backLink}
        to="/animes/$animeId"
        params={{ animeId: playback.anime_id }}
      >
        ← Back to anime
      </Link>

      <header className={styles.header}>
        <p className={styles.kicker}>Episode {playback.episode_number}</p>
        <h1 className={styles.title}>{playback.title}</h1>
        {playback.duration_seconds !== null ? (
          <p>{formatDuration(playback.duration_seconds)}</p>
        ) : null}
      </header>

      <section className={styles.panel}>
        <VideoPlayer
          playback={playback}
          onRetryMedia={async () => {
            const result = await query.refetch();
            if (result.isError || result.data === undefined) {
              throw result.error instanceof Error
                ? result.error
                : new Error("Playback refresh failed.");
            }
            return result.data;
          }}
        />
      </section>
    </main>
  );
}

function formatDuration(value: number): string {
  const totalSeconds = Math.max(0, Math.floor(value));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return (
      String(hours).padStart(2, "0") +
      ":" +
      String(minutes).padStart(2, "0") +
      ":" +
      String(seconds).padStart(2, "0")
    );
  }

  return (
    String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0")
  );
}
