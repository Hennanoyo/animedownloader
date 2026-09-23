import { useState } from "react";
import { useForm } from "@tanstack/react-form";
import {
  Button,
  Form,
  Input,
  Label,
  Text,
  TextField,
} from "react-aria-components";
import type {
  Anime,
  Episode,
  EpisodeInput,
} from "../../../entities/anime/model/types";
import type { Release } from "../../../entities/release/model/types";
import ReleasePicker from "../../release-picker/ui/ReleasePicker";
import {
  episodeCreateFormSchema,
  episodeEditFormSchema,
  type EpisodeFormValues,
} from "../model/schema";
import {
  useCreateEpisode,
  useDeleteEpisode,
  useUpdateEpisode,
} from "../model/useEpisodeManagement";
import styles from "./EpisodeManagement.module.scss";

interface Props {
  anime: Anime;
}

export default function EpisodeManagement({ anime }: Props) {
  const [isAdding, setIsAdding] = useState(false);
  const [editingEpisodeId, setEditingEpisodeId] = useState<string | null>(
    null,
  );
  const [deletingEpisodeId, setDeletingEpisodeId] = useState<string | null>(
    null,
  );
  const deleteMutation = useDeleteEpisode(anime.id);

  async function confirmDelete() {
    if (!deletingEpisodeId) {
      return;
    }

    await deleteMutation.mutateAsync(deletingEpisodeId);
    setDeletingEpisodeId(null);
  }

  return (
    <section
      className={styles.section}
      aria-labelledby="episode-management-heading"
    >
      <div className={styles.header}>
        <div>
          <p className={styles.kicker}>Episode management</p>
          <h2 id="episode-management-heading">Episodes</h2>
          <p>Add new releases, change episode metadata, or remove episodes.</p>
        </div>
        <Button
          className={styles.primaryButton}
          onPress={() => {
            setEditingEpisodeId(null);
            setDeletingEpisodeId(null);
            setIsAdding((value) => !value);
          }}
        >
          {isAdding ? "Close" : "Add episode"}
        </Button>
      </div>

      {isAdding ? (
        <EpisodeEditor
          animeId={anime.id}
          mode="create"
          onCancel={() => setIsAdding(false)}
          onSaved={() => setIsAdding(false)}
        />
      ) : null}

      {anime.episodes.length === 0 && !isAdding ? (
        <p className={styles.warning}>No episodes have been added yet.</p>
      ) : (
        <div className={styles.list}>
          {anime.episodes.map((episode) => (
            <article className={styles.row} key={episode.id}>
              {editingEpisodeId === episode.id ? (
                <EpisodeEditor
                  animeId={anime.id}
                  episode={episode}
                  mode="edit"
                  onCancel={() => setEditingEpisodeId(null)}
                  onSaved={() => setEditingEpisodeId(null)}
                />
              ) : (
                <>
                  <div className={styles.rowHeader}>
                    <div>
                      <strong className={styles.title}>
                        #{episode.episode_number} · {episode.title}
                      </strong>
                      <span className={styles.meta}>
                        {episode.source_title ?? episode.source}
                      </span>
                    </div>
                    <div className={styles.buttons}>
                      <Button
                        className={styles.button}
                        onPress={() => {
                          setIsAdding(false);
                          setDeletingEpisodeId(null);
                          setEditingEpisodeId(episode.id);
                        }}
                      >
                        Edit
                      </Button>
                      <Button
                        className={styles.dangerButton}
                        onPress={() => {
                          setDeletingEpisodeId(episode.id);
                          setIsAdding(false);
                          setEditingEpisodeId(null);
                        }}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>

                  {deletingEpisodeId === episode.id ? (
                    <div
                      className={styles.confirm}
                      role="alertdialog"
                      aria-label="Delete episode confirmation"
                    >
                      <p>
                        Delete episode #{episode.episode_number}? This removes
                        only the episode record; the Anime remains.
                      </p>
                      {deleteMutation.isError ? (
                        <p className={styles.error} role="alert">
                          Failed to delete episode:{" "}
                          {deleteMutation.error.message}
                        </p>
                      ) : null}
                      <div className={styles.buttons}>
                        <Button
                          className={styles.cancelButton}
                          onPress={() => setDeletingEpisodeId(null)}
                          isDisabled={deleteMutation.isPending}
                        >
                          Cancel
                        </Button>
                        <Button
                          className={styles.dangerButton}
                          onPress={() => void confirmDelete()}
                          isDisabled={deleteMutation.isPending}
                        >
                          {deleteMutation.isPending
                            ? "Deleting..."
                            : "Delete episode"}
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

interface EpisodeEditorProps {
  animeId: string;
  episode?: Episode;
  mode: "create" | "edit";
  onCancel: () => void;
  onSaved: () => void;
}

function EpisodeEditor({
  animeId,
  episode,
  mode,
  onCancel,
  onSaved,
}: EpisodeEditorProps) {
  const createMutation = useCreateEpisode(animeId);
  const updateMutation = useUpdateEpisode();
  const [releaseChanged, setReleaseChanged] = useState(mode === "create");
  const initialRelease = episode ? toRelease(episode) : null;
  const isPending = createMutation.isPending || updateMutation.isPending;
  const error = createMutation.error ?? updateMutation.error;

  const form = useForm({
    defaultValues: {
      episode_number: episode?.episode_number ?? 1,
      title: episode?.title ?? "",
      release: initialRelease,
    } satisfies EpisodeFormValues,
    validators: {
      onSubmit:
        mode === "create" ? episodeCreateFormSchema : episodeEditFormSchema,
    },
    onSubmit: async ({ value }) => {
      if (mode === "create") {
        const release = value.release;
        if (release === null) {
          throw new Error(
            "Every new episode must have a selected Nyaa release.",
          );
        }

        await createMutation.mutateAsync(toCreateInput(value, release));
      } else if (episode) {
        await updateMutation.mutateAsync({
          episodeId: episode.id,
          input: toUpdateInput(value, releaseChanged),
        });
      }

      onSaved();
    },
  });

  return (
    <div className={styles.editor}>
      <div className={styles.rowHeader}>
        <div>
          <strong>{mode === "create" ? "Add episode" : "Edit episode"}</strong>
          <span className={styles.meta}>
            Episode numbers must be unique within this Anime.
          </span>
        </div>
      </div>

      <Form
        onSubmit={(event) => {
          event.preventDefault();
          void form.handleSubmit();
        }}
      >
        <form.Field name="title">
          {(field) => (
            <TextField
              className={styles.field}
              isRequired
              isInvalid={
                !field.state.meta.isValid ||
                field.state.value.trim().length === 0
              }
              validationBehavior="aria"
            >
              <Label>Episode title</Label>
              <Input
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
                placeholder="Frieren - 01"
              />
              {!field.state.meta.isValid ? (
                <Text slot="errorMessage">
                  {field.state.meta.errors.map(String).join(", ")}
                </Text>
              ) : null}
            </TextField>
          )}
        </form.Field>

        <form.Field name="episode_number">
          {(field) => (
            <TextField
              className={styles.field}
              isRequired
              isInvalid={
                !field.state.meta.isValid ||
                !Number.isInteger(field.state.value) ||
                field.state.value < 1 ||
                field.state.value > 9999
              }
              validationBehavior="aria"
            >
              <Label>Episode number</Label>
              <Input
                type="number"
                inputMode="numeric"
                value={String(field.state.value)}
                onBlur={field.handleBlur}
                onChange={(event) =>
                  field.handleChange(Number(event.target.value))
                }
              />
              {!field.state.meta.isValid ? (
                <Text slot="errorMessage">
                  {field.state.meta.errors.map(String).join(", ")}
                </Text>
              ) : null}
            </TextField>
          )}
        </form.Field>

        <form.Field name="release">
          {(field) => (
            <>
              <ReleasePicker
                release={field.state.value}
                onSelect={(release) => {
                  setReleaseChanged(true);
                  field.handleChange(release);
                }}
              />
              {mode === "create" && !field.state.value ? (
                <Text className={styles.warning}>
                  Select a Nyaa release before saving.
                </Text>
              ) : null}
            </>
          )}
        </form.Field>

        {error ? (
          <p className={styles.error} role="alert">
            Failed to {mode === "create" ? "create" : "update"} episode:{" "}
            {error.message}
          </p>
        ) : null}

        <div className={styles.actions}>
          <div className={styles.buttons}>
            <Button
              type="button"
              className={styles.cancelButton}
              onPress={onCancel}
              isDisabled={isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className={styles.primaryButton}
              isDisabled={isPending}
            >
              {isPending
                ? "Saving..."
                : mode === "create"
                  ? "Add episode"
                  : "Save episode"}
            </Button>
          </div>
        </div>
      </Form>
    </div>
  );
}

function toRelease(episode: Episode): Release {
  return {
    source: episode.source,
    id: episode.source_id ?? episode.id,
    title: episode.source_title ?? episode.title,
    page_url: episode.source_url ?? episode.torrent_url,
    torrent_url: episode.torrent_url,
    published_at: null,
    size: episode.size,
    seeders: episode.seeders,
    leechers: episode.leechers,
    downloads: episode.downloads,
    info_hash: episode.info_hash,
  };
}

function toCreateInput(
  value: EpisodeFormValues,
  release: Release,
): EpisodeInput {
  return {
    episode_number: value.episode_number,
    title: value.title.trim(),
    source: release.source,
    source_id: release.id,
    source_title: release.title,
    source_url: release.page_url,
    torrent_url: release.torrent_url,
    size: release.size,
    seeders: release.seeders,
    leechers: release.leechers,
    downloads: release.downloads,
    info_hash: release.info_hash,
  };
}

function toUpdateInput(
  value: EpisodeFormValues,
  releaseChanged: boolean,
): Partial<EpisodeInput> {
  const input: Partial<EpisodeInput> = {
    episode_number: value.episode_number,
    title: value.title.trim(),
  };

  if (releaseChanged && value.release) {
    input.source = value.release.source;
    input.source_id = value.release.id;
    input.source_title = value.release.title;
    input.source_url = value.release.page_url;
    input.torrent_url = value.release.torrent_url;
    input.size = value.release.size;
    input.seeders = value.release.seeders;
    input.leechers = value.release.leechers;
    input.downloads = value.release.downloads;
    input.info_hash = value.release.info_hash;
  }

  return input;
}
