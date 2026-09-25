import { z } from "zod";
import { getJson } from "../../../shared/api/client";
import type {
  ReleaseDiscoveryInput,
  ReleaseDiscoveryResponse,
} from "../model/types";

const releaseSchema = z.object({
  source: z.string(),
  id: z.string(),
  title: z.string(),
  page_url: z.string().url(),
  torrent_url: z.string().url(),
  published_at: z.coerce.date().nullable(),
  size: z.string().nullable(),
  seeders: z.number().int().nonnegative().nullable(),
  leechers: z.number().int().nonnegative().nullable(),
  downloads: z.number().int().nonnegative().nullable(),
  info_hash: z.string().nullable(),
});

const parsedReleaseSchema = z.object({
  provider_source: z.string(),
  source_id: z.string(),
  original_title: z.string(),
  normalized_title: z.string(),
  release_group: z.string().nullable(),
  series_title: z.string().nullable(),
  episode_number: z.number().int().positive().nullable(),
  episode_title: z.string().nullable(),
  season_number: z.number().int().positive().nullable(),
  resolution: z.string().nullable(),
  source: z.string().nullable(),
  video_codec: z.string().nullable(),
  audio_codec: z.string().nullable(),
  bit_depth: z.number().int().positive().nullable(),
  status: z.enum(["parsed", "ambiguous", "unparsed", "unsupported"]),
  warnings: z.array(z.string()),
  failed_required_fields: z.array(z.string()),
  parser_profile_version: z.number().int().positive().nullable(),
});

const animeMatchSchema = z.object({
  status: z.enum(["matched", "ambiguous", "unmatched"]),
  normalized_series_title: z.string().nullable(),
  candidates: z.array(
    z.object({
      anime_id: z.string().uuid(),
      title: z.string(),
      matched_titles: z.array(z.string()),
    }),
  ),
});

const responseSchema = z.object({
  query: z.string(),
  warnings: z.array(z.string()),
  search_profile_version: z.number().int().positive().nullable(),
  items: z.array(
    z.object({
      release: releaseSchema,
      parsed: parsedReleaseSchema,
      match: animeMatchSchema,
    }),
  ),
});

export class ReleaseDiscoveryResponseError extends Error {
  constructor(readonly issues: z.core.$ZodIssue[]) {
    super(
      "Invalid release discovery response: " +
        issues
          .map(
            (issue) =>
              (issue.path.join(".") || "<root>") + ": " + issue.message,
          )
          .join("; "),
    );
    this.name = "ReleaseDiscoveryResponseError";
  }
}

export async function discoverReleases(
  input: ReleaseDiscoveryInput,
  signal?: AbortSignal,
): Promise<ReleaseDiscoveryResponse> {
  const params = new URLSearchParams({ title: input.title });
  for (const field of input.fields) params.append("fields", field);
  if (input.group) params.set("group", input.group);
  if (input.episode !== undefined) params.set("episode", String(input.episode));
  if (input.resolution) params.set("resolution", input.resolution);
  if (input.codec) params.set("codec", input.codec);

  const payload = await getJson(
    "/api/releases/discover?" + params.toString(),
    { signal },
  );
  const result = responseSchema.safeParse(payload);
  if (!result.success) {
    throw new ReleaseDiscoveryResponseError(result.error.issues);
  }
  return result.data;
}
