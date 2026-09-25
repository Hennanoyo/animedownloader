import { useMemo, useState } from "react";
import { useForm } from "@tanstack/react-form";
import {
  Button,
  Checkbox,
  Form,
  Input,
  Label,
  Text,
  TextField,
} from "react-aria-components";
import { z } from "zod";
import { ApiRequestError } from "../../../shared/api/client";
import { ReleaseDiscoveryResponseError } from "../../../entities/release/api/discoverReleases";
import type {
  ReleaseDiscoveryInput,
  ReleaseDiscoveryItem,
  SearchField,
} from "../../../entities/release/model/types";
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
  group: "Release group",
  title: "Anime title",
  episode: "Episode",
  resolution: "Resolution",
  codec: "Video codec",
};

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

export default function ReleaseDiscoveryPanel({
  animeTitle,
}: {
  animeTitle: string;
}) {
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

  const form = useForm({
    defaultValues: {
      title: animeTitle,
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
          Runs exactly one Nyaa search per click. Enable, disable, or reorder
          fields, then edit their values before searching again.
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
            <p>Enabled fields are sent in the order shown here.</p>
          </div>

          <ol className={styles.fieldOrder}>
            {fieldOrder.map((field, index) => {
              const label = FIELD_LABELS[field];
              return (
                <li className={styles.fieldOrderItem} key={field}>
                  <Checkbox
                    isSelected={enabledFields[field]}
                    onChange={(selected) =>
                      setEnabledFields((current) => ({
                        ...current,
                        [field]: selected,
                      }))
                    }
                  >
                    <span className={styles.checkboxMark} aria-hidden="true" />
                    <span>{label}</span>
                  </Checkbox>

                  <div className={styles.orderButtons}>
                    <Button
                      type="button"
                      className={styles.orderButton}
                      onPress={() =>
                        setFieldOrder((current) =>
                          moveField(current, field, -1),
                        )
                      }
                      isDisabled={index === 0}
                      aria-label={"Move " + label + " up"}
                    >
                      ↑
                    </Button>
                    <Button
                      type="button"
                      className={styles.orderButton}
                      onPress={() =>
                        setFieldOrder((current) =>
                          moveField(current, field, 1),
                        )
                      }
                      isDisabled={index === fieldOrder.length - 1}
                      aria-label={"Move " + label + " down"}
                    >
                      ↓
                    </Button>
                  </div>
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

        <div className={styles.fields}>
          <form.Field name="title">
            {(field) => (
              <TextField
                className={styles.field}
                isRequired
                isInvalid={field.state.meta.errors.length > 0}
                validationBehavior="aria"
              >
                <Label>Anime title</Label>
                <Input
                  value={field.state.value}
                  placeholder="Sousou no Frieren"
                  onBlur={field.handleBlur}
                  onChange={(event) => field.handleChange(event.target.value)}
                />
                {field.state.meta.errors.length > 0 ? (
                  <Text slot="errorMessage">
                    {String(field.state.meta.errors[0])}
                  </Text>
                ) : null}
              </TextField>
            )}
          </form.Field>

          <form.Field name="group">
            {(field) => (
              <TextField className={styles.field} validationBehavior="aria">
                <Label>Release group</Label>
                <Input
                  value={field.state.value}
                  placeholder="ExampleSubs"
                  onBlur={field.handleBlur}
                  onChange={(event) => field.handleChange(event.target.value)}
                />
              </TextField>
            )}
          </form.Field>

          <form.Field name="episode">
            {(field) => (
              <TextField
                className={styles.field}
                isInvalid={field.state.meta.errors.length > 0}
                validationBehavior="aria"
              >
                <Label>Episode</Label>
                <Input
                  type="number"
                  inputMode="numeric"
                  value={field.state.value}
                  placeholder="08"
                  onBlur={field.handleBlur}
                  onChange={(event) => field.handleChange(event.target.value)}
                />
                {field.state.meta.errors.length > 0 ? (
                  <Text slot="errorMessage">
                    {String(field.state.meta.errors[0])}
                  </Text>
                ) : null}
              </TextField>
            )}
          </form.Field>

          <form.Field name="resolution">
            {(field) => (
              <TextField className={styles.field} validationBehavior="aria">
                <Label>Resolution</Label>
                <Input
                  value={field.state.value}
                  placeholder="1080p"
                  onBlur={field.handleBlur}
                  onChange={(event) => field.handleChange(event.target.value)}
                />
              </TextField>
            )}
          </form.Field>

          <form.Field name="codec">
            {(field) => (
              <TextField className={styles.field} validationBehavior="aria">
                <Label>Video codec</Label>
                <Input
                  value={field.state.value}
                  placeholder="HEVC"
                  onBlur={field.handleBlur}
                  onChange={(event) => field.handleChange(event.target.value)}
                />
              </TextField>
            )}
          </form.Field>
        </div>

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
