import { useEffect, useState } from "react";
import {
  Button,
  Form,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select,
  SelectValue,
  TextField,
} from "react-aria-components";
import { useForm } from "@tanstack/react-form";
import { useNavigate } from "@tanstack/react-router";
import type {
  CreateAnimeInput,
  Season,
  Weekday,
} from "../../../entities/anime/model/types";
import { useCreateAnime } from "../model/useCreateAnime";
import {
  animeCreateFormSchema,
  type AnimeCreateFormValues,
  type AnimeEpisodeDraft,
} from "../model/schema";
import ReleasePicker from "./ReleasePicker";
import styles from "./AnimeCreateForm.module.scss";

const seasons: Array<{ value: Season; label: string }> = [
  { value: "winter", label: "Winter" },
  { value: "spring", label: "Spring" },
  { value: "summer", label: "Summer" },
  { value: "fall", label: "Fall" },
];

const weekdays: Array<{ value: Weekday; label: string }> = [
  { value: "monday", label: "Monday" },
  { value: "tuesday", label: "Tuesday" },
  { value: "wednesday", label: "Wednesday" },
  { value: "thursday", label: "Thursday" },
  { value: "friday", label: "Friday" },
  { value: "saturday", label: "Saturday" },
  { value: "sunday", label: "Sunday" },
];

function emptyEpisode(number: number): AnimeEpisodeDraft {
  return { episode_number: number, title: "", release: null };
}

function toCreateInput(value: AnimeCreateFormValues): CreateAnimeInput {
  return {
    title: value.title.trim(),
    year: value.year,
    season: value.season,
    weekday: value.weekday,
    air_time: value.air_time || null,
    timezone: value.timezone.trim(),
    episodes: value.episodes.map((episode) => {
      const release = episode.release;

      if (release === null) {
        throw new Error("Every episode must have a selected Nyaa release.");
      }

      return {
        episode_number: episode.episode_number,
        title: episode.title.trim(),
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
    }),
  };
}

function duplicateNumbers(episodes: AnimeEpisodeDraft[]): number[] {
  const counts = new Map<number, number>();

  for (const episode of episodes) {
    counts.set(
      episode.episode_number,
      (counts.get(episode.episode_number) ?? 0) + 1,
    );
  }

  return Array.from(counts.entries())
    .filter(([, count]) => count > 1)
    .map(([number]) => number)
    .sort((a, b) => a - b);
}

export default function AnimeCreateForm() {
  const navigate = useNavigate();
  const mutation = useCreateAnime();
  const [episodes, setEpisodes] = useState<AnimeEpisodeDraft[]>([
    emptyEpisode(1),
  ]);

  const form = useForm<AnimeCreateFormValues>({
    defaultValues: {
      title: "",
      year: new Date().getFullYear(),
      season: "fall",
      weekday: "friday",
      air_time: "",
      timezone: "Asia/Tokyo",
      episodes,
    },
    validators: {
      onSubmit: animeCreateFormSchema,
    },
    onSubmit: async ({ value }) => {
      await mutation.mutateAsync(toCreateInput(value));
      await navigate({ to: "/animes" });
    },
  });

  useEffect(() => {
    form.setFieldValue("episodes", episodes);
  }, [episodes, form]);

  function updateEpisode(index: number, update: Partial<AnimeEpisodeDraft>) {
    setEpisodes((current) =>
      current.map((episode, episodeIndex) =>
        episodeIndex === index ? { ...episode, ...update } : episode,
      ),
    );
  }

  function addEpisode() {
    setEpisodes((current) => {
      const max = current.reduce(
        (value, episode) => Math.max(value, episode.episode_number),
        0,
      );
      return [...current, emptyEpisode(max + 1)];
    });
  }

  function removeEpisode(index: number) {
    setEpisodes((current) =>
      current.length === 1
        ? current
        : current.filter((_, episodeIndex) => episodeIndex !== index),
    );
  }

  const duplicates = duplicateNumbers(episodes);

  return (
    <Form
      className={styles.form}
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit();
      }}
    >
      <div className={styles.grid}>
        <form.Field name="title">
          {(field) => (
            <TextField className={styles.field} isRequired>
              <Label>Title</Label>
              <Input
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
                placeholder="Frieren: Beyond Journey's End"
              />
            </TextField>
          )}
        </form.Field>

        <form.Field name="year">
          {(field) => (
            <TextField className={styles.field} isRequired>
              <Label>Year</Label>
              <Input
                type="number"
                inputMode="numeric"
                value={String(field.state.value)}
                onBlur={field.handleBlur}
                onChange={(event) =>
                  field.handleChange(Number(event.target.value))
                }
              />
            </TextField>
          )}
        </form.Field>

        <form.Field name="season">
          {(field) => (
            <Select
              className={styles.field}
              selectedKey={field.state.value}
              onSelectionChange={(key) =>
                field.handleChange(String(key) as Season)
              }
            >
              <Label>Season</Label>
              <Button className={styles.selectButton} type="button">
                <SelectValue />
              </Button>
              <Popover className={styles.popover}>
                <ListBox>
                  {seasons.map((option) => (
                    <ListBoxItem id={option.value} key={option.value}>
                      {option.label}
                    </ListBoxItem>
                  ))}
                </ListBox>
              </Popover>
            </Select>
          )}
        </form.Field>

        <form.Field name="weekday">
          {(field) => (
            <Select
              className={styles.field}
              selectedKey={field.state.value}
              onSelectionChange={(key) =>
                field.handleChange(String(key) as Weekday)
              }
            >
              <Label>Weekday</Label>
              <Button className={styles.selectButton} type="button">
                <SelectValue />
              </Button>
              <Popover className={styles.popover}>
                <ListBox>
                  {weekdays.map((option) => (
                    <ListBoxItem id={option.value} key={option.value}>
                      {option.label}
                    </ListBoxItem>
                  ))}
                </ListBox>
              </Popover>
            </Select>
          )}
        </form.Field>

        <form.Field name="air_time">
          {(field) => (
            <TextField className={styles.field}>
              <Label>Air time</Label>
              <Input
                type="time"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
            </TextField>
          )}
        </form.Field>

        <form.Field name="timezone">
          {(field) => (
            <TextField className={styles.field}>
              <Label>Timezone</Label>
              <Input
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
            </TextField>
          )}
        </form.Field>
      </div>

      <section className={styles.episodes}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Episodes</h2>
            <p>Select a Nyaa release for each episode, then clean up the episode title.</p>
          </div>
          <Button
            type="button"
            className={styles.secondaryButton}
            onPress={addEpisode}
          >
            Add episode
          </Button>
        </div>

        {duplicates.length > 0 ? (
          <p className={styles.warning}>
            Duplicate episode numbers: {duplicates.join(", ")}.
          </p>
        ) : null}

        {episodes.map((episode, index) => (
          <article className={styles.episode} key={index}>
            <div className={styles.episodeHeader}>
              <strong>Episode {index + 1}</strong>
              <Button
                type="button"
                className={styles.removeButton}
                onPress={() => removeEpisode(index)}
                isDisabled={episodes.length === 1}
              >
                Remove
              </Button>
            </div>

            <TextField className={styles.field} isRequired>
              <Label>Episode number</Label>
              <Input
                type="number"
                inputMode="numeric"
                value={String(episode.episode_number)}
                onChange={(event) =>
                  updateEpisode(index, {
                    episode_number: Number(event.target.value),
                  })
                }
              />
            </TextField>

            <TextField className={styles.field} isRequired>
              <Label>Episode title</Label>
              <Input
                value={episode.title}
                onChange={(event) =>
                  updateEpisode(index, { title: event.target.value })
                }
                placeholder="Frieren - 01"
              />
            </TextField>

            <ReleasePicker
              release={episode.release}
              onSelect={(release) => {
                updateEpisode(index, {
                  release,
                  title: episode.title.trim() ? episode.title : release.title,
                });
              }}
            />

            {!episode.release ? (
              <p className={styles.warning}>
                Select a Nyaa release before submitting this anime.
              </p>
            ) : null}
          </article>
        ))}
      </section>

      {mutation.isError ? (
        <p className={styles.formError}>
          Failed to create anime: {mutation.error.message}
        </p>
      ) : null}

      <div className={styles.actions}>
        <Button
          type="button"
          className={styles.cancelButton}
          onPress={() => void navigate({ to: "/animes" })}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          className={styles.primaryButton}
          isDisabled={form.state.isSubmitting || mutation.isPending}
        >
          {mutation.isPending ? "Creating..." : "Create anime"}
        </Button>
      </div>
    </Form>
  );
}
