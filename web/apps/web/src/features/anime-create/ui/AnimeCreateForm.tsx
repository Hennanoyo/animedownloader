import { useState } from "react";
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
  Text,
  TextField,
} from "react-aria-components";
import { useForm } from "@tanstack/react-form";
import { useNavigate } from "@tanstack/react-router";
import type {
  CreateAnimeInput,
  Season,
  Weekday,
} from "../../../entities/anime/model/types";
import { formatZodIssues } from "../../../shared/lib/validation";
import { useCreateAnime } from "../model/useCreateAnime";
import {
  animeCreateFormSchema,
  type AnimeCreateFormValues,
  type AnimeEpisodeDraft,
} from "../model/schema";
import ReleasePicker from "../../release-picker/ui/ReleasePicker";
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
    titles: Object.fromEntries(
      Object.entries(value.titles)
        .map(([key, title]) => [key, title.trim()])
        .filter(([, title]) => title !== ""),
    ),
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

function getSubmitErrors(errorMap: unknown): string[] {
  const messages: string[] = [];

  function visit(value: unknown, path: string[] = []) {
    if (Array.isArray(value)) {
      for (const item of value) visit(item, path);
      return;
    }

    if (typeof value === "string") {
      if (value.trim()) {
        messages.push(path.length > 0 ? path.join(".") + ": " + value : value);
      }
      return;
    }

    if (value === null || typeof value !== "object") {
      return;
    }

    if (
      "message" in value &&
      typeof value.message === "string" &&
      value.message.trim()
    ) {
      const message = value.message.trim();
      messages.push(path.length > 0 ? path.join(".") + ": " + message : message);
    }

    for (const [key, child] of Object.entries(value)) {
      if (
        key === "message" ||
        key === "code" ||
        key === "path" ||
        key === "onSubmit" ||
        key === "onChange" ||
        key === "onBlur"
      ) {
        visit(child, path);
        continue;
      }
      visit(child, [...path, key]);
    }
  }

  visit(errorMap);
  return Array.from(new Set(messages));
}

export default function AnimeCreateForm() {
  const navigate = useNavigate();
  const mutation = useCreateAnime();
  const [submitValidationErrors, setSubmitValidationErrors] = useState<string[]>(
    [],
  );

  const defaultValues: AnimeCreateFormValues = {
    title: "",
    titles: { romaji: "", jp: "", ko: "", en: "" },
    year: new Date().getFullYear(),
    season: "fall",
    weekday: "friday",
    air_time: "",
    timezone: "Asia/Tokyo",
    episodes: [],
  };

  const form = useForm({
    defaultValues,
    validators: {
      onSubmit: animeCreateFormSchema,
    },
    onSubmit: async ({ value }) => {
      setSubmitValidationErrors([]);
      await mutation.mutateAsync(toCreateInput(value));
      await navigate({ to: "/animes" });
    },
    onSubmitInvalid: ({ value }) => {
      const result = animeCreateFormSchema.safeParse(value);
      if (result.success) {
        setSubmitValidationErrors([]);
        return;
      }

      const rootMessages = result.error.issues
        .filter((issue) => issue.path.length === 0)
        .map((issue) => issue.message);

      setSubmitValidationErrors(
        Array.from(
          new Set(
            rootMessages.length > 0
              ? rootMessages
              : [formatZodIssues(result.error.issues)],
          ),
        ),
      );
    },
  });

  const submitErrors = [
    ...submitValidationErrors,
    ...getSubmitErrors(form.state.errorMap.onSubmit),
  ].filter((error, index, errors) => errors.indexOf(error) === index);

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
            <TextField
              className={styles.field}
              isRequired
              isInvalid={!field.state.meta.isValid}
              validationBehavior="aria"
            >
              <Label>Title</Label>
              <Input
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
                placeholder="Frieren: Beyond Journey's End"
              />
              {!field.state.meta.isValid ? (
                <Text slot="errorMessage" className={styles.fieldError}>
                  {field.state.meta.errors.map(String).join(", ")}
                </Text>
              ) : null}
            </TextField>
          )}
        </form.Field>

        <form.Field name="titles.romaji">
          {(field) => (
            <TextField className={styles.field} validationBehavior="aria">
              <Label>Romaji title</Label>
              <Input
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
                placeholder="Sousou no Frieren"
              />
            </TextField>
          )}
        </form.Field>

        <form.Field name="titles.jp">
          {(field) => (
            <TextField className={styles.field} validationBehavior="aria">
              <Label>Japanese title</Label>
              <Input
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
            </TextField>
          )}
        </form.Field>

        <form.Field name="titles.ko">
          {(field) => (
            <TextField className={styles.field} validationBehavior="aria">
              <Label>Korean title</Label>
              <Input
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
            </TextField>
          )}
        </form.Field>

        <form.Field name="titles.en">
          {(field) => (
            <TextField className={styles.field} validationBehavior="aria">
              <Label>English title</Label>
              <Input
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
            </TextField>
          )}
        </form.Field>

        <form.Field name="year">
          {(field) => (
            <TextField
              className={styles.field}
              isRequired
              isInvalid={!field.state.meta.isValid}
              validationBehavior="aria"
            >
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
              {!field.state.meta.isValid ? (
                <Text slot="errorMessage" className={styles.fieldError}>
                  {field.state.meta.errors.map(String).join(", ")}
                </Text>
              ) : null}
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
            <TextField
              className={styles.field}
              isInvalid={!field.state.meta.isValid}
              validationBehavior="aria"
            >
              <Label>Air time</Label>
              <Input
                type="time"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              {!field.state.meta.isValid ? (
                <Text slot="errorMessage" className={styles.fieldError}>
                  {field.state.meta.errors.map(String).join(", ")}
                </Text>
              ) : null}
            </TextField>
          )}
        </form.Field>

        <form.Field name="timezone">
          {(field) => (
            <TextField
              className={styles.field}
              isInvalid={!field.state.meta.isValid}
              validationBehavior="aria"
            >
              <Label>Timezone</Label>
              <Input
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              {!field.state.meta.isValid ? (
                <Text slot="errorMessage" className={styles.fieldError}>
                  {field.state.meta.errors.map(String).join(", ")}
                </Text>
              ) : null}
            </TextField>
          )}
        </form.Field>
      </div>

      <section className={styles.episodes}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Episodes</h2>
            <p>
              Select a Nyaa release for each episode, then clean up the episode
              title.
            </p>
          </div>
          <form.Field name="episodes" mode="array">
            {(episodesField) => (
              <Button
                type="button"
                className={styles.secondaryButton}
                onPress={() => {
                  const max = episodesField.state.value.reduce(
                    (value, episode) => Math.max(value, episode.episode_number),
                    0,
                  );
                  episodesField.pushValue(emptyEpisode(max + 1));
                }}
              >
                Add episode
              </Button>
            )}
          </form.Field>
        </div>

        <form.Field name="episodes" mode="array">
          {(episodesField) => {
            const duplicates = duplicateNumbers(episodesField.state.value);

            return (
              <>
                {duplicates.length > 0 ? (
                  <p className={styles.warning}>
                    Duplicate episode numbers: {duplicates.join(", ")}.
                  </p>
                ) : null}

        {submitErrors.length > 0 ? (
          <div className={styles.formError} role="alert" aria-live="polite">
            <strong>Check the form before creating the anime.</strong>
            <ul className={styles.errorList}>
              {submitErrors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          </div>
        ) : null}

                {episodesField.state.value.map((episode, index) => (
                  <article className={styles.episode} key={index}>
                    <div className={styles.episodeHeader}>
                      <strong>Episode {episode.episode_number}</strong>
                      <Button
                        type="button"
                        className={styles.removeButton}
                        onPress={() => episodesField.removeValue(index)}
                      >
                        Remove
                      </Button>
                    </div>

            <TextField
              className={styles.field}
              isRequired
              isInvalid={episode.title.trim().length === 0}
              validationBehavior="aria"
            >
              <Label>Episode title</Label>
              <Input
                value={episode.title}
                onChange={(event) =>
                  updateEpisode(index, { title: event.target.value })
                }
                placeholder="Frieren - 01"
              />
              {episode.title.trim().length === 0 ? (
                <Text slot="errorMessage" className={styles.fieldError}>
                  Enter an episode title.
                </Text>
              ) : null}
            </TextField>

                    <form.Field name={`episodes[${index}].episode_number`}>
                      {(field) => (
                        <TextField
                          className={styles.field}
                          isRequired
                          isInvalid={
                            !Number.isInteger(field.state.value) ||
                            field.state.value < 1 ||
                            field.state.value > 9999 ||
                            duplicates.includes(field.state.value)
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
                          {duplicates.includes(field.state.value) ? (
                            <Text slot="errorMessage" className={styles.fieldError}>
                              Episode number must be unique.
                            </Text>
                          ) : null}
                        </TextField>
                      )}
                    </form.Field>

                    <ReleasePicker
                      release={episode.release}
                      onSelect={(release) => {
                        episodesField.replaceValue(index, {
                          ...episodesField.state.value[index],
                          release,
                          title: episodesField.state.value[index].title.trim()
                            ? episodesField.state.value[index].title
                            : release.title,
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

                {episodesField.state.value.length === 0 ? (
                  <div className={styles.emptyEpisodes}>
                    <p>No episodes added yet.</p>
                    <span>Use Add episode to add the first episode.</span>
                  </div>
                ) : null}
              </>
            );
          }}
        </form.Field>
      </section>

      {mutation.isError ? (
        <p className={styles.formError} role="alert" aria-live="polite">
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
          type="button"
          className={styles.primaryButton}
          onPress={() => void form.handleSubmit()}
          isDisabled={form.state.isSubmitting || mutation.isPending}
        >
          {mutation.isPending ? "Creating..." : "Create anime"}
        </Button>
      </div>
    </Form>
  );
}
