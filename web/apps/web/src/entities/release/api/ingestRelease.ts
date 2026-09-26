import { z } from "zod";
import { formatZodIssues } from "../../../shared/lib/validation";
import { postJson } from "../../../shared/api/client";
import type {
  EpisodeIngestionInput,
  EpisodeIngestionResponse,
  EpisodeReleaseReplacementInput,
} from "../model/types";

const episodeSchema = z.object({
  id: z.uuid(),
  anime_id: z.uuid(),
  release_group_id: z.uuid().nullable(),
  episode_number: z.number().int().positive(),
  title: z.string(),
  source: z.string(),
  source_id: z.string().nullable(),
  source_title: z.string().nullable(),
  source_url: z.string().url().nullable(),
  torrent_url: z.string().url(),
  size: z.string().nullable(),
  seeders: z.number().int().nonnegative().nullable(),
  leechers: z.number().int().nonnegative().nullable(),
  downloads: z.number().int().nonnegative().nullable(),
  info_hash: z.string().nullable(),
  download_status: z.enum([
    "not_started",
    "downloading",
    "completed",
    "failed",
  ]),
  conversion_status: z.enum([
    "not_started",
    "converting",
    "completed",
    "failed",
  ]),
  created_at: z.coerce.date(),
  updated_at: z.coerce.date(),
});

const responseSchema = z.object({
  status: z.enum(["created", "idempotent", "replacement_candidate", "replaced"]),
  episode: episodeSchema.nullable(),
  existing_episode: episodeSchema.nullable(),
});

export class EpisodeIngestionResponseError extends Error {
  constructor(readonly issues: z.core.$ZodIssue[]) {
    super(
      "Invalid episode ingestion response: " + formatZodIssues(issues),
    );
    this.name = "EpisodeIngestionResponseError";
  }
}

export async function ingestRelease(
  input: EpisodeIngestionInput,
): Promise<EpisodeIngestionResponse> {
  const payload = await postJson("/api/releases/ingest", input);
  const result = responseSchema.safeParse(payload);
  if (!result.success) {
    throw new EpisodeIngestionResponseError(result.error.issues);
  }
  return result.data;
}


export async function replaceEpisodeRelease(
  episodeId: string,
  input: EpisodeReleaseReplacementInput,
): Promise<EpisodeIngestionResponse> {
  const payload = await postJson(
    "/api/releases/episodes/" + episodeId + "/replace",
    input,
  );
  const result = responseSchema.safeParse(payload);
  if (!result.success) {
    throw new EpisodeIngestionResponseError(result.error.issues);
  }
  return result.data;
}
