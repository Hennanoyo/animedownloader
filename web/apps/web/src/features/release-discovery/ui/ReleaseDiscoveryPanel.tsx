import { useMemo, useState } from "react";
import { useForm } from "@tanstack/react-form";
import {
  Button,
  Checkbox,
  ComboBox,
  Form,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Text,
} from "react-aria-components";
import { z } from "zod";
import { ApiRequestError } from "../../../shared/api/client";
import type { EpisodeIngestionResponse } from "../../../entities/release/model/types";

import { ReleaseDiscoveryResponseError } from "../../../entities/release/api/discoverReleases";
import type {
  ReleaseDiscoveryInput,
  ReleaseDiscoveryItem,
  SearchField,
} from "../../../entities/release/model/types";
import { useReleaseGroups } from "../../../entities/release/model/useReleaseGroups";
import { useReleaseDiscovery } from "../model/useReleaseDiscovery";
import { useIngestRelease, useReplaceRelease } from "../model/useIngestRelease";
import styles from "./ReleaseDiscoveryPanel.module.scss";

const schema = z.object({
  title: z
    .string()
    .trim()
    .min(1, "Enter an anime title.")
    .max(200, "Anime title must be 200 characters or fewer."),
  group: z.string().trim().max(128, "Release group is too long."),
  episode: z.string().trim().refine(
    (value) =>
      value === "" ||
      (/^\d+$/.test(value) && Number(value) >= 1 && Number(value) <= 9999),
    "Episode must be between 1 and 9999.",
  ),
  resolution: z.string().trim().max(32, "Resolution is too long."),
  codec: z.string().trim().max(32, "Codec is too long."),
});

const DEFAULT_FIELD_ORDER: SearchField[] = [
  "group",
  "title",
  "episode",
  "resolution",
  "codec",
];

const FIELD_LABELS: Record<SearchField, string> = {
  group: "Group",
  title: "Title",
  episode: "Episode",
  resolution: "Resolution",
  codec: "Codec",
};

const EPISODE_OPTIONS = Array.from({ length: 24 }, (_, index) =>
  String(index + 1).padStart(2, "0"),
);
const RESOLUTION_OPTIONS = ["2160p", "1080p", "720p", "480p"];
const CODEC_OPTIONS = ["HEVC", "AVC", "AV1", "VP9"];

export type ReleaseDiscoveryTitleSource =
  | "romaji"
  | "jp"
  | "ko"
  | "en"
  | "main"
  | "custom";

export interface ReleaseDiscoveryTitleOption {
  key: ReleaseDiscoveryTitleSource;
  label: string;
  value: string;
}

type Values = z.infer<typeof schema>;

function getFieldValue(values: Values, field: SearchField): string {
  switch (field) {
    case "group":
      return values.group;
    case "title":
      return values.title;
    case "episode":
      return values.episode;
    case "resolution":
      return values.resolution;
    case "codec":
      return values.codec;
  }
}

function buildQueryPreview(values: Values, fields: SearchField[]): string {
  return fields
    .map((field) => getFieldValue(values, field).trim())
    .filter(Boolean)
    .join(" ");
}

function moveField(
  order: SearchField[],
  field: SearchField,
  direction: -1 | 1,
): SearchField[] {
  const index = order.indexOf(field);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= order.length) return order;

  const next = [...order];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

function moveFieldToTarget(
  order: SearchField[],
  field: SearchField,
  targetField: SearchField,
  placeAfter: boolean,
): SearchField[] {
  if (field === targetField) return order;

  const next = order.filter((item) => item !== field);
  const targetIndex = next.indexOf(targetField);
  const insertIndex = targetIndex + (placeAfter ? 1 : 0);
  next.splice(insertIndex, 0, field);
  return next;
}

function getTitleOption(
  options: ReleaseDiscoveryTitleOption[],
  key: ReleaseDiscoveryTitleSource,
): ReleaseDiscoveryTitleOption {
  return (
    options.find((option) => option.key === key) ??
    options.find((option) => option.key === "main") ??
    options[0]
  );
}

export default function ReleaseDiscoveryPanel({
  animeId,
  titleOptions,
  defaultTitleSource,
}: {
  animeId: string;
  titleOptions: ReleaseDiscoveryTitleOption[];
  defaultTitleSource: ReleaseDiscoveryTitleSource;
}) {
  const initialTitleOption = getTitleOption(titleOptions, defaultTitleSource);
  const releaseGroups = useReleaseGroups();
  const [request, setRequest] = useState<ReleaseDiscoveryInput | null>(null);
  const [fieldOrder, setFieldOrder] =
    useState<SearchField[]>(DEFAULT_FIELD_ORDER);
  const [enabledFields, setEnabledFields] =
    useState<Record<SearchField, boolean>>({
      group: true,
      title: true,
      episode: true,
      resolution: true,
      codec: true,
    });
  const [draggedField, setDraggedField] = useState<SearchField | null>(null);
  const [dropTarget, setDropTarget] = useState<{
    field: SearchField;
    placeAfter: boolean;
  } | null>(null);
  const [keyboardGrabbedField, setKeyboardGrabbedField] =
    useState<SearchField | null>(null);
  const [dragAnnouncement, setDragAnnouncement] = useState("");

  const form = useForm({
    defaultValues: {
      title: initialTitleOption.value,
      group: "",
      episode: "",
      resolution: "",
      codec: "",
    },
    validators: { onSubmit: schema },
    onSubmit: ({ value }) => {
      const fields = fieldOrder.filter((field) => enabledFields[field]);
      if (!buildQueryPreview(value, fields)) return;

      setRequest({
        anime_id: animeId,
        title: value.title.trim(),
        fields,
        ...(value.group.trim() ? { group: value.group.trim() } : {}),
        ...(value.episode.trim()
          ? { episode: Number(value.episode.trim()) }
          : {}),
        ...(value.resolution.trim()
          ? { resolution: value.resolution.trim() }
          : {}),
        ...(value.codec.trim() ? { codec: value.codec.trim() } : {}),
      });
    },
  });

  const query = useReleaseDiscovery(request);
  const activeFields = useMemo(
    () => fieldOrder.filter((field) => enabledFields[field]),
    [enabledFields, fieldOrder],
  );

  function handleDragStart(
    event: React.DragEvent<HTMLButtonElement>,
    field: SearchField,
  ) {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", field);
    setDraggedField(field);
    setDropTarget(null);
    setDragAnnouncement(
      `Dragging ${FIELD_LABELS[field]}. Drop it before or after another field.`,
    );
  }

  function handleDragOver(
    event: React.DragEvent<HTMLLIElement>,
    field: SearchField,
  ) {
    if (!draggedField || draggedField === field) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";

    const rect = event.currentTarget.getBoundingClientRect();
    const placeAfter = event.clientY > rect.top + rect.height / 2;
    setDropTarget({ field, placeAfter });
  }

  function handleDrop(event: React.DragEvent<HTMLLIElement>, field: SearchField) {
    event.preventDefault();

    const source =
      (event.dataTransfer.getData("text/plain") as SearchField) ||
      draggedField;
    if (!source || source === field) {
      setDraggedField(null);
      setDropTarget(null);
      return;
    }

    const placeAfter =
      dropTarget?.field === field ? dropTarget.placeAfter : false;
    const nextOrder = moveFieldToTarget(
      fieldOrder,
      source,
      field,
      placeAfter,
    );
    setFieldOrder(nextOrder);
    setDraggedField(null);
    setDropTarget(null);
    setDragAnnouncement(
      `${FIELD_LABELS[source]} moved ${placeAfter ? "after" : "before"} ${FIELD_LABELS[field]}.`,
    );
  }

  function handleReorderKeyDown(
    event: React.KeyboardEvent<HTMLButtonElement>,
    field: SearchField,
  ) {
    if (event.key === " ") {
      event.preventDefault();
      const grabbing = keyboardGrabbedField === field;
      setKeyboardGrabbedField(grabbing ? null : field);
      setDragAnnouncement(
        grabbing
          ? `${FIELD_LABELS[field]} released.`
          : `${FIELD_LABELS[field]} grabbed. Use Arrow Up or Arrow Down to move it, then Space to release.`,
      );
      return;
    }

    if (event.key === "Escape" && keyboardGrabbedField === field) {
      event.preventDefault();
      setKeyboardGrabbedField(null);
      setDragAnnouncement(`${FIELD_LABELS[field]} released.`);
      return;
    }

    if (
      keyboardGrabbedField !== field ||
      (event.key !== "ArrowUp" && event.key !== "ArrowDown")
    ) {
      return;
    }

    event.preventDefault();
    const direction = event.key === "ArrowUp" ? -1 : 1;
    const nextOrder = moveField(fieldOrder, field, direction);
    if (nextOrder === fieldOrder) return;

    setFieldOrder(nextOrder);
    const position = nextOrder.indexOf(field) + 1;
    setDragAnnouncement(
      `${FIELD_LABELS[field]} moved to position ${position} of ${nextOrder.length}.`,
    );
  }

  return (
    <section
      className={styles.panel}
      aria-labelledby="release-discovery-heading"
      aria-label="Find releases"
    >
      <div>
        <p className={styles.kicker}>Release discovery</p>
        <h2 id="release-discovery-heading">Find releases</h2>
        <p className={styles.description}>
          Runs the configured search plan against Nyaa. Reorder fields by dragging
          them, or use the keyboard handle to move them before searching.
        </p>
      </div>

      <Form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          void form.handleSubmit();
        }}
      >
        <section
          className={styles.queryConfig}
          aria-labelledby="search-fields-heading"
        >
          <div>
            <h3 id="search-fields-heading">Search fields</h3>
            <p>
              Check the fields to include, edit values inline, and drag rows to
              change query order.
            </p>
          </div>

          <p id="search-fields-reorder-help" className={styles.srOnly}>
            Drag handles support mouse dragging. For keyboard access, focus a
            handle, press Space, use Arrow Up or Arrow Down to move the field,
            then press Space again.
          </p>

          <ol className={styles.fieldOrder}>
            {fieldOrder.map((field) => {
              const label = FIELD_LABELS[field];
              const isDropTarget = dropTarget?.field === field;

              return (
                <li
                  className={styles.fieldOrderItem}
                  data-search-field={field}
                  data-drop-position={
                    isDropTarget
                      ? dropTarget.placeAfter
                        ? "after"
                        : "before"
                      : undefined
                  }
                  key={field}
                  onDragOver={(event) => handleDragOver(event, field)}
                  onDragLeave={() => {
                    if (dropTarget?.field === field) {
                      setDropTarget(null);
                    }
                  }}
                  onDrop={(event) => handleDrop(event, field)}
                >
                  <button
                    type="button"
                    className={styles.dragHandle}
                    draggable
                    aria-describedby="search-fields-reorder-help"
                    aria-label={`Reorder ${label}`}
                    aria-pressed={keyboardGrabbedField === field}
                    data-drag-handle={field}
                    onDragStart={(event) => handleDragStart(event, field)}
                    onDragEnd={() => {
                      setDraggedField(null);
                      setDropTarget(null);
                    }}
                    onKeyDown={(event) => handleReorderKeyDown(event, field)}
                  >
                    <span aria-hidden="true">☰</span>
                  </button>

                  <Checkbox
                    className={styles.fieldToggle}
                    data-search-field-toggle={field}
                    isSelected={enabledFields[field]}
                    onChange={(selected) =>
                      setEnabledFields((current) => ({
                        ...current,
                        [field]: selected,
                      }))
                    }
                    aria-label={`Enable ${label}`}
                  >
                    <span className={styles.checkboxMark} aria-hidden="true" />
                  </Checkbox>

                  <div className={styles.fieldMeta}>
                    <span className={styles.fieldLabel}>{label}</span>
                  </div>

                  <form.Field name={field}>
                    {(fieldState) => {
                      const options =
                        field === "title"
                          ? titleOptions
                              .filter(
                                (option) =>
                                  option.key !== "custom" &&
                                  option.value.trim().length > 0,
                              )
                              .map((option) => option.value)
                          : field === "group"
                            ? (releaseGroups.data?.map((group) => group.name) ?? [])
                            : field === "episode"
                              ? EPISODE_OPTIONS
                              : field === "resolution"
                                ? RESOLUTION_OPTIONS
                                : CODEC_OPTIONS;

                      return (
                        <ComboBox
                          className={styles.inlineComboBox}
                          items={options}
                          inputValue={String(fieldState.state.value)}
                          allowsCustomValue
                          isInvalid={fieldState.state.meta.errors.length > 0}
                          onInputChange={(value) => {
                            fieldState.handleChange(value);
                          }}
                          onSelectionChange={(key) => {
                            if (field !== "title" || key === null) return;
                            const option = titleOptions.find(
                              (candidate) => candidate.value === String(key),
                            );
                            if (option && option.value.trim().length > 0) {
                              form.setFieldValue("title", option.value);
                            }
                          }}
                        >
                          <Label className={styles.inlineLabel}>{label}</Label>
                          <div className={styles.comboControl}>
                            <Input
                              aria-label={label}
                              placeholder={
                                field === "title"
                                  ? "Sousou no Frieren"
                                  : field === "group"
                                    ? "ExampleSubs"
                                    : field === "episode"
                                      ? "08"
                                      : field === "resolution"
                                        ? "1080p"
                                        : "HEVC"
                              }
                              onBlur={fieldState.handleBlur}
                            />
                            <Button aria-label={"Show " + label + " options"}>
                              ▾
                            </Button>
                          </div>
                          <Popover className={styles.selectPopover}>
                            <ListBox className={styles.selectListBox}>
                              {(option: string) => {
                                const titleOption = titleOptions.find(
                                  (candidate) => candidate.value === option,
                                );

                                return (
                                  <ListBoxItem
                                    id={option}
                                    textValue={option}
                                    className={styles.selectItem}
                                  >
                                    {titleOption ? (
                                      <>
                                        <span>{titleOption.label}</span>
                                        <span className={styles.titleOptionValue}>
                                          {titleOption.value}
                                        </span>
                                      </>
                                    ) : (
                                      option
                                    )}
                                  </ListBoxItem>
                                );
                              }}
                            </ListBox>
                          </Popover>
                          {fieldState.state.meta.errors.length > 0 ? (
                            <Text slot="errorMessage">
                              {String(fieldState.state.meta.errors[0])}
                            </Text>
                          ) : null}
                        </ComboBox>
                      );
                    }}
                  </form.Field>
                </li>
              );
            })}
          </ol>

          <form.Subscribe selector={({ values }) => values}>
            {(values) => (
              <div className={styles.preview}>
                <strong>Query preview</strong>
                <code>
                  {buildQueryPreview(values, activeFields) ||
                    "Select at least one non-empty field."}
                </code>
              </div>
            )}
          </form.Subscribe>
        </section>

        <div className={styles.actions}>
          <Button
            className={styles.searchButton}
            type="submit"
            isDisabled={form.state.isSubmitting || query.isFetching}
          >
            {query.isFetching ? "Searching..." : "Discover releases"}
          </Button>
          {request ? (
            <span className={styles.searchState}>
              {query.isFetching
                ? "Searching Nyaa"
                : query.data
                  ? query.data.items.length + " candidates"
                  : "Ready"}
            </span>
          ) : null}
        </div>
      </Form>

      {query.isError ? (
        <p className={styles.error} role="alert">
          {getErrorMessage(query.error)}
        </p>
      ) : null}

      {query.isSuccess ? (
        <DiscoveryResults
          animeId={animeId}
          items={query.data.items}
          queries={query.data.queries}
          warnings={query.data.warnings}
          profileVersion={query.data.search_profile_version}
        />
      ) : null}

      <div className={styles.srOnly} aria-live="polite" aria-atomic="true">
        {dragAnnouncement}
      </div>
    </section>
  );
}

interface DiscoveryResultsProps {
  animeId: string;
  items: ReleaseDiscoveryItem[];
  queries: string[];
  warnings: string[];
  profileVersion: number | null;
}

function DiscoveryResults({
  animeId,
  items,
  queries,
  warnings,
  profileVersion,
}: DiscoveryResultsProps) {
  const ingest = useIngestRelease(animeId);
  const replace = useReplaceRelease(animeId);
  const [ingestions, setIngestions] = useState<
    Record<string, EpisodeIngestionResponse>
  >({});

  async function handleIngest(item: ReleaseDiscoveryItem) {
    const result = await ingest.mutateAsync({
      release: item.release,
      parsed: item.parsed,
    });
    setIngestions((current) => ({
      ...current,
      [item.release.id]: result,
    }));
  }

  async function handleReplace(
    item: ReleaseDiscoveryItem,
    episodeId: string,
  ) {
    const result = await replace.mutateAsync({
      episodeId,
      release: item.release,
      parsed: item.parsed,
    });
    setIngestions((current) => ({
      ...current,
      [item.release.id]: result,
    }));
  }
  return (
    <div className={styles.results} aria-live="polite">
      <div className={styles.resultsMeta}>
        <div>
          <strong>{items.length} candidates</strong>
          <span>
            {profileVersion
              ? "Search profile v" + profileVersion
              : "Default field order"}
          </span>
        </div>
        <details className={styles.queries}>
          <summary>
            {queries.length === 1 ? "Query" : String(queries.length) + " queries"}
          </summary>
          <div>
            {queries.map((value) => (
              <code key={value}>{value}</code>
            ))}
          </div>
        </details>
      </div>

      {warnings.map((warning) => (
        <p className={styles.warning} key={warning}>
          {warning}
        </p>
      ))}

      {items.length === 0 ? (
        <p className={styles.empty}>No matching releases were found.</p>
      ) : (
        <div className={styles.list}>
          {items.map((item) => {
            const ingestion = ingestions[item.release.id];
            const existingEpisode = ingestion?.existing_episode;

            return (
              <article className={styles.card} key={item.release.id}>
              <div className={styles.cardHeader}>
                <div>
                  <h3>{item.release.title}</h3>
                  <p>{formatReleaseMeta(item)}</p>
                </div>
                {item.ranking.score > 0 ? (
                  <span className={styles.rankBadge}>
                    Preferred {item.ranking.score}
                  </span>
                ) : null}
                <span
                  className={styles.status}
                  data-status={item.parsed.status}
                >
                  {item.parsed.status}
                </span>
              </div>

              <div className={styles.parsed}>
                <span>
                  <strong>Series</strong>
                  {item.parsed.series_title ?? "—"}
                </span>
                <span>
                  <strong>Episode</strong>
                  {item.parsed.episode_number ?? "—"}
                </span>
                <span>
                  <strong>Group</strong>
                  {item.parsed.release_group ?? "—"}
                </span>
                <span>
                  <strong>Resolution</strong>
                  {item.parsed.resolution ?? "—"}
                </span>
                <span>
                  <strong>Codec</strong>
                  {item.parsed.video_codec ?? "—"}
                </span>
                <span>
                  <strong>Parser</strong>
                  {item.parsed.parser_profile_version
                    ? "v" + item.parsed.parser_profile_version
                    : "Generic"}
                </span>
              </div>

              {item.ranking.reasons.length > 0 ? (
                <p className={styles.rankingReasons}>
                  {item.ranking.reasons.join(" · ")}
                </p>
              ) : null}

              {item.parsed.warnings.length > 0 ? (
                <p className={styles.itemWarning}>
                  {item.parsed.warnings.join(" · ")}
                </p>
              ) : null}

              <div className={styles.matchPanel}>
                <div>
                  <strong>Anime match</strong>
                  <span>
                    {item.match.status === "matched"
                      ? item.match.candidates.length === 1
                        ? item.match.candidates[0]?.matched_titles.join(" · ") ||
                          "Exact title match"
                        : "Exact title match"
                      : item.match.status === "ambiguous"
                        ? item.match.candidates.length + " Anime candidates"
                        : "No Anime candidate"}
                  </span>
                </div>
                <div className={styles.matchActions}>
                  {item.match.candidates.some(
                    (candidate) => candidate.anime_id === animeId,
                  ) ? (
                    <Button
                      className={styles.ingestButton}
                      onPress={() => void handleIngest(item)}
                      isDisabled={
                        item.parsed.status !== "parsed" ||
                        item.parsed.episode_number === null ||
                        ingest.isPending
                      }
                    >
                      {ingest.isPending &&
                      ingest.variables?.release.id === item.release.id
                        ? "Adding..."
                        : "Add to this Anime"}
                    </Button>
                  ) : (
                    <span
                      className={styles.matchStatus}
                      data-status={item.match.status}
                    >
                      {item.match.status === "unmatched"
                        ? "No match"
                        : "Does not match this Anime"}
                    </span>
                  )}
                </div>
              </div>

              {ingestion ? (
                <div
                  className={styles.ingestResult}
                  data-status={ingestion.status}
                >
                  <p>{formatIngestionResult(ingestion)}</p>
                  {ingestion.status === "replacement_candidate" &&
                  existingEpisode ? (
                    <div className={styles.replacementActions}>
                      <span>
                        Existing release:{" "}
                        {existingEpisode.source_title ?? "Unknown"}
                      </span>
                      <Button
                        className={styles.replaceButton}
                        onPress={() =>
                          void handleReplace(item, existingEpisode.id)
                        }
                        isDisabled={
                          replace.isPending ||
                          item.parsed.status !== "parsed" ||
                          item.parsed.episode_number === null
                        }
                      >
                        {replace.isPending &&
                        replace.variables?.episodeId === existingEpisode.id
                          ? "Replacing..."
                          : "Replace release"}
                      </Button>
                    </div>
                  ) : null}
                  {replace.isError ? (
                    <p className={styles.error} role="alert">
                      Failed to replace release: {replace.error.message}
                    </p>
                  ) : null}
                </div>
              ) : null}

              <div className={styles.links}>
                <a
                  href={item.release.page_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  View release
                </a>
                <a
                  href={item.release.torrent_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Torrent
                </a>
              </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

function formatReleaseMeta(item: ReleaseDiscoveryItem): string {
  return [
    item.release.size ?? "Unknown size",
    "Seeders " + (item.release.seeders ?? 0),
    item.parsed.source ?? "Source unknown",
  ].join(" · ");
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ReleaseDiscoveryResponseError) return error.message;
  if (error instanceof ApiRequestError) return error.message;
  if (error instanceof Error) return error.message;
  return "Release discovery failed.";
}


function formatIngestionResult(result: EpisodeIngestionResponse): string {
  if (result.status === "created" && result.episode) {
    return "Episode " + result.episode.episode_number + " added to this Anime.";
  }
  if (result.status === "idempotent" && result.episode) {
    return (
      "Episode " +
      result.episode.episode_number +
      " was already linked; release metadata was refreshed."
    );
  }
  if (result.status === "replaced" && result.episode) {
    return (
      "Episode " +
      result.episode.episode_number +
      " release was replaced."
    );
  }
  if (result.existing_episode) {
    return (
      "Episode " +
      result.existing_episode.episode_number +
      " already exists with another release. Replacement review is required."
    );
  }
  return "Ingestion completed.";
}
