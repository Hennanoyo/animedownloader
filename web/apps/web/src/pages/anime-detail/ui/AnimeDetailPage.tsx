import { useState } from "react";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { Button } from "react-aria-components";
import type { Anime } from "../../../entities/anime/model/types";
import { useAnimeDetail } from "../../../features/anime-detail/model/useAnimeDetail";
import { useDeleteAnime } from "../../../features/anime-edit/model/useEditAnime";
import AnimeEditForm from "../../../features/anime-edit/ui/AnimeEditForm";
import EpisodeDownloadControl from "../../../features/episode-download/ui/EpisodeDownloadControl";
import EpisodeManagement from "../../../features/episode-management/ui/EpisodeManagement";
import { ApiRequestError } from "../../../shared/api/client";
import styles from "./AnimeDetailPage.module.scss";

export default function AnimeDetailPage() {
  const { animeId } = useParams({ from: "/animes/$animeId" });
  const query = useAnimeDetail(animeId);
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);

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

  const anime = query.data;

  return (
    <main className={styles.page}>
      <Link className={styles.backLink} to="/animes">
        ← Back to anime
      </Link>

      {isEditing ? (
        <section className={styles.editPanel} aria-labelledby="edit-heading">
          <div className={styles.panelHeader}>
            <div>
              <p className={styles.kicker}>Anime management</p>
              <h1 id="edit-heading">Edit anime</h1>
              <p className={styles.panelDescription}>
                Update the anime information and manage the episodes belonging
                to this Anime.
              </p>
            </div>
          </div>
          <AnimeEditForm
            anime={anime}
            onCancel={() => setIsEditing(false)}
            onSaved={() => void query.refetch()}
          />
          <EpisodeManagement anime={anime} />
        </section>
      ) : (
        <AnimeHeader
          anime={anime}
          onDeleteConfirm={() => setIsDeleteConfirmOpen(true)}
          onEdit={() => {
            setIsEditing(true);
            setIsDeleteConfirmOpen(false);
          }}
        />
      )}

      {!isEditing && isDeleteConfirmOpen ? (
        <DeleteAnimeConfirmation
          anime={anime}
          onCancel={() => setIsDeleteConfirmOpen(false)}
        />
      ) : null}

      {!isEditing ? (
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
                      <EpisodeDownloadControl episodeId={episode.id} />
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
      ) : null}
    </main>
  );
}

interface AnimeHeaderProps {
  anime: Anime;
  onDeleteConfirm: () => void;
  onEdit: () => void;
}

function AnimeHeader({
  anime,
  onDeleteConfirm,
  onEdit,
}: AnimeHeaderProps) {
  return (
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
      <div className={styles.headerActions}>
        <span className={styles.episodeCount}>
          {anime.episodes.length} episodes
        </span>
        <Button className={styles.secondaryButton} onPress={onEdit}>
          Edit
        </Button>
        <Button className={styles.dangerButton} onPress={onDeleteConfirm}>
          Delete
        </Button>
      </div>
    </header>
  );
}

interface DeleteAnimeConfirmationProps {
  anime: Anime;
  onCancel: () => void;
}

function DeleteAnimeConfirmation({
  anime,
  onCancel,
}: DeleteAnimeConfirmationProps) {
  const navigate = useNavigate();
  const mutation = useDeleteAnime(anime.id);

  async function handleDelete() {
    await mutation.mutateAsync();
    await navigate({ to: "/animes" });
  }

  return (
    <section
      className={styles.deletePanel}
      role="alertdialog"
      aria-labelledby="delete-heading"
      aria-describedby="delete-description"
    >
      <div>
        <p className={styles.kicker}>Delete anime</p>
        <h2 id="delete-heading">Delete {anime.title}?</h2>
        <p id="delete-description">
          This permanently removes the anime and its episodes. This action
          cannot be undone.
        </p>
      </div>

      {mutation.isError ? (
        <p className={styles.deleteError} role="alert">
          Failed to delete anime: {mutation.error.message}
        </p>
      ) : null}

      <div className={styles.headerActions}>
        <Button
          className={styles.secondaryButton}
          onPress={onCancel}
          isDisabled={mutation.isPending}
        >
          Cancel
        </Button>
        <Button
          className={styles.dangerButton}
          onPress={() => void handleDelete()}
          isDisabled={mutation.isPending}
        >
          {mutation.isPending ? "Deleting..." : "Delete anime"}
        </Button>
      </div>
    </section>
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
