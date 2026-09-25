import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { Button } from "react-aria-components";
import Icon from "../../../shared/ui/Icon";
import type { Anime } from "../../../entities/anime/model/types";
import { useAnimeDetail } from "../../../features/anime-detail/model/useAnimeDetail";
import {
  useAnimePipeline,
} from "../../../features/anime-detail/model/useAnimePipeline";
import { useAnimePipelineRealtime } from "../../../features/anime-detail/model/useAnimePipelineRealtime";
import { useDeleteAnime } from "../../../features/anime-edit/model/useEditAnime";
import AnimeEditForm from "../../../features/anime-edit/ui/AnimeEditForm";
import EpisodeManagement from "../../../features/episode-management/ui/EpisodeManagement";
import EpisodePipelineCard from "../../../widgets/episode-pipeline/ui/EpisodePipelineCard";
import { ApiRequestError } from "../../../shared/api/client";
import styles from "./AnimeDetailPage.module.scss";

export default function AnimeDetailPage() {
  const { animeId } = useParams({ from: "/animes/$animeId" });
  const queryClient = useQueryClient();
  const query = useAnimeDetail(animeId);
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const realtime = useAnimePipelineRealtime({
    animeId,
    enabled: !isEditing,
  });
  const pipelineQuery = useAnimePipeline(animeId, realtime.connected);

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
            onSaved={() => {
              void query.refetch();
              void queryClient.invalidateQueries({
                queryKey: ["anime-pipelines", animeId],
              });
            }}
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
        <section
          className={styles.pipelineSummary}
          aria-labelledby="episodes-heading"
        >
          <div className={styles.panelHeader}>
            <div>
              <p className={styles.kicker}>Media pipeline</p>
              <h2 id="episodes-heading">Episodes</h2>
            </div>
          </div>

          {pipelineQuery.isPending ? (
            <p className={styles.pipelineState}>Loading media status...</p>
          ) : pipelineQuery.isError ? (
            <div className={styles.pipelineState} role="alert">
              <p>
                Failed to load media pipeline status.
                {pipelineQuery.error instanceof Error
                  ? " " + pipelineQuery.error.message
                  : ""}
              </p>
              <Button
                className={styles.pipelineRetryButton}
                onPress={() => void pipelineQuery.refetch()}
              >
                Retry
              </Button>
            </div>
          ) : pipelineQuery.data.episodes.length === 0 ? (
            <p className={styles.pipelineState}>
              No episodes have been added yet.
            </p>
          ) : (
            <div className={styles.pipelineList}>
              {anime.episodes.map((episode) => {
                const pipeline = pipelineQuery.data.episodes.find(
                  (item) => item.episode_id === episode.id,
                );
                return pipeline ? (
                  <EpisodePipelineCard
                    key={episode.id}
                    episode={episode}
                    pipeline={pipeline}
                    realtimeConnected={realtime.connected}
                  />
                ) : null;
              })}
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
        <div className={styles.headerMeta}>
          <p className={styles.schedule}>
            {anime.year} · {formatLabel(anime.season)} ·{" "}
            {formatLabel(anime.weekday)} ·{" "}
            {anime.air_time ?? "Time not set"} ({anime.timezone})
          </p>
          <span className={styles.episodeCount}>
            {anime.episodes.length} {anime.episodes.length === 1 ? "episode" : "episodes"}
          </span>
        </div>
      </div>
      <div className={styles.headerActions}>
        <Button
          className={styles.iconHeaderButton}
          onPress={onEdit}
          aria-label="Edit anime"
        >
          <Icon name="edit" size={17} />
        </Button>
        <Button
          className={styles.iconHeaderButtonDanger}
          onPress={onDeleteConfirm}
          aria-label="Delete anime"
        >
          <Icon name="trash" size={17} />
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

