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
import { ReleaseDiscoveryResponseError } from "../../../entities/release/api/discoverReleases";
import type {
  ReleaseDiscoveryInput,
  ReleaseDiscoveryItem,
  SearchField,
} from "../../../entities/release/model/types";
import { useReleaseGroups } from "../../../entities/release/model/useReleaseGroups";
import { useReleaseDiscovery } from "../model/useReleaseDiscovery";
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
  titleOptions,
  defaultTitleSource,
}: {
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
          Runs exactly one Nyaa search per click. Reorder fields by dragging
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
                    {field === "title" ? (
                      <span className={styles.fieldHint}>
                        Choose a saved title or type a custom value
                      </span>
                    ) : null}
                  </div>

                  <form.Field name={field}>
                    {(fieldState) => {
                      const options =
                        field === "title"
                          ? titleOptions.filter(
                              (option) =>
                                option.key !== "custom" &&
                                option.value.trim().length > 0,
                            )
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
                              (candidate) => candidate.key === String(key),
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
                              {(option: string | ReleaseDiscoveryTitleOption) => {
                                if (typeof option === "string") {
                                  return (
                                    <ListBoxItem
                                      id={option}
                                      textValue={option}
                                      className={styles.selectItem}
                                    >
                                      {option}
                                    </ListBoxItem>
                                  );
                                }

                                return (
                                  <ListBoxItem
                                    id={option.key}
                                    textValue={option.value}
                                    className={styles.selectItem}
                                  >
                                    <span>{option.label}</span>
                                    <span className={styles.titleOptionValue}>
                                      {option.value}
                                    </span>
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
          items={query.data.items}
          query={query.data.query}
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
  items: ReleaseDiscoveryItem[];
  query: string;
  warnings: string[];
  profileVersion: number | null;
}

function DiscoveryResults({
  items,
  query,
  warnings,
  profileVersion,
}: DiscoveryResultsProps) {
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
          <summary>Query</summary>
          <code>{query}</code>
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
          {items.map((item) => (
            <article className={styles.card} key={item.release.id}>
              <div className={styles.cardHeader}>
                <div>
                  <h3>{item.release.title}</h3>
                  <p>{formatReleaseMeta(item)}</p>
                </div>
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

              {item.parsed.warnings.length > 0 ? (
                <p className={styles.itemWarning}>
                  {item.parsed.warnings.join(" · ")}
                </p>
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
          ))}
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
