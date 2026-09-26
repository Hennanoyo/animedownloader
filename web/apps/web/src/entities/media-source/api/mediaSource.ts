import { z } from "zod";
import { deleteJson, getJson, postJson } from "../../../shared/api/client";
import { formatZodIssues } from "../../../shared/lib/validation";
import type {
  EpisodeMediaSource,
  MediaSourceActionResult,
  MediaSourceOrphan,
} from "../model/types";

const mediaSourceSchema = z.object({
  episode_id: z.uuid(),
  download_job_id: z.uuid().nullable(),
  download_status: z
    .enum([
      "pending",
      "downloading",
      "paused",
      "completed",
      "failed",
      "cancelled",
    ])
    .nullable(),
  status: z.enum([
    "not_available",
    "found",
    "missing_directory",
    "no_media",
    "ambiguous",
  ]),
  root: z.string().nullable(),
  selected_path: z.string().nullable(),
  candidates: z.array(z.object({ path: z.string() })),
  processing_job_id: z.uuid().nullable(),
  processing_status: z
    .enum(["pending", "processing", "completed", "failed"])
    .nullable(),
});

const actionResultSchema = z.object({
  stage: z.enum(["download", "processing"]),
  job_id: z.uuid(),
  status: z.literal("pending"),
});

const orphanSchema = z.object({
  directory_id: z.uuid(),
  path: z.string(),
});

export class MediaSourceResponseError extends Error {
  constructor(readonly issues: z.core.$ZodIssue[]) {
    super("Invalid media source API response: " + formatZodIssues(issues));
    this.name = "MediaSourceResponseError";
  }
}

async function parseMediaSource(payload: unknown): Promise<EpisodeMediaSource> {
  const result = mediaSourceSchema.safeParse(payload);
  if (!result.success) {
    throw new MediaSourceResponseError(result.error.issues);
  }
  return result.data;
}

export async function getEpisodeMediaSource(
  episodeId: string,
  signal?: AbortSignal,
): Promise<EpisodeMediaSource> {
  return parseMediaSource(
    await getJson("/api/episodes/" + episodeId + "/media-source", { signal }),
  );
}

export async function reprocessEpisodeMediaSource(
  episodeId: string,
  signal?: AbortSignal,
): Promise<MediaSourceActionResult> {
  const result = actionResultSchema.safeParse(
    await postJson(
      "/api/episodes/" + episodeId + "/media-source/reprocess",
      {},
      { signal },
    ),
  );
  if (!result.success) {
    throw new MediaSourceResponseError(result.error.issues);
  }
  return result.data;
}

export async function redownloadEpisodeMediaSource(
  episodeId: string,
  signal?: AbortSignal,
): Promise<MediaSourceActionResult> {
  const result = actionResultSchema.safeParse(
    await postJson(
      "/api/episodes/" + episodeId + "/media-source/redownload",
      {},
      { signal },
    ),
  );
  if (!result.success) {
    throw new MediaSourceResponseError(result.error.issues);
  }
  return result.data;
}

export async function selectEpisodeMediaSource(
  episodeId: string,
  path: string,
  signal?: AbortSignal,
): Promise<MediaSourceActionResult> {
  const result = actionResultSchema.safeParse(
    await postJson(
      "/api/episodes/" + episodeId + "/media-source/select",
      { path },
      { signal },
    ),
  );
  if (!result.success) {
    throw new MediaSourceResponseError(result.error.issues);
  }
  return result.data;
}

export async function listMediaSourceOrphans(
  signal?: AbortSignal,
): Promise<MediaSourceOrphan[]> {
  const payload = await getJson("/api/media-sources/orphans", { signal });
  const result = z.array(orphanSchema).safeParse(payload);
  if (!result.success) {
    throw new MediaSourceResponseError(result.error.issues);
  }
  return result.data;
}

export async function deleteMediaSourceOrphan(
  directoryId: string,
  signal?: AbortSignal,
): Promise<void> {
  await deleteJson("/api/media-sources/orphans/" + directoryId, { signal });
}
