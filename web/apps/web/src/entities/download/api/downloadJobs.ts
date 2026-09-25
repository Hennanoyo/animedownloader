import { z } from "zod";
import { deleteJson, getJson, postJson } from "../../../shared/api/client";
import type {
  DownloadJob,
  DownloadJobListParams,
  DownloadJobListResponse,
} from "../model/types";

const downloadJobSchema = z.object({
  id: z.uuid(),
  episode_id: z.uuid(),
  status: z.enum([
    "pending",
    "downloading",
    "paused",
    "completed",
    "failed",
    "cancelled",
  ]),
  downloaded_bytes: z.number().int().nonnegative(),
  total_bytes: z.number().int().nonnegative().nullable(),
  attempt_count: z.number().int().nonnegative(),
  error_message: z.string().nullable(),
  started_at: z.coerce.date().nullable(),
  completed_at: z.coerce.date().nullable(),
  created_at: z.coerce.date(),
  updated_at: z.coerce.date(),
});

const downloadJobListItemSchema = downloadJobSchema.extend({
  anime_id: z.uuid(),
  anime_title: z.string(),
  episode_number: z.number().int().positive(),
  episode_title: z.string(),
});

const downloadJobListResponseSchema = z.object({
  items: z.array(downloadJobListItemSchema),
  page: z.number().int().positive(),
  page_size: z.number().int().positive(),
  total: z.number().int().nonnegative(),
  has_more: z.boolean(),
});

export class DownloadJobResponseError extends Error {
  constructor(readonly issues: z.core.$ZodIssue[]) {
    super(
      "Invalid download job API response: " +
        issues
          .map(
            (issue) =>
              (issue.path.join(".") || "<root>") + ": " + issue.message,
          )
          .join("; "),
    );
    this.name = "DownloadJobResponseError";
  }
}


export async function listDownloadJobs(
  params: DownloadJobListParams = {},
): Promise<DownloadJobListResponse> {
  const search = new URLSearchParams();
  for (const status of params.statuses ?? []) {
    search.append("status", status);
  }
  search.set("page", String(params.page ?? 1));
  search.set("page_size", String(params.pageSize ?? 100));

  const result = downloadJobListResponseSchema.safeParse(
    await getJson("/api/download-jobs?" + search.toString(), {
      signal: params.signal,
    }),
  );
  if (!result.success) {
    throw new DownloadJobResponseError(result.error.issues);
  }
  return result.data;
}

export async function getLatestEpisodeDownloadJob(
  episodeId: string,
  signal?: AbortSignal,
): Promise<DownloadJob | null> {
  const payload = await getJson(
    "/api/episodes/" + episodeId + "/download-jobs/latest",
    { signal },
  );

  if (payload === null) {
    return null;
  }

  return parseDownloadJob(payload);
}

export async function createEpisodeDownloadJob(
  episodeId: string,
  signal?: AbortSignal,
): Promise<DownloadJob> {
  return parseDownloadJob(
    await postJson(
      "/api/episodes/" + episodeId + "/download-jobs",
      {},
      { signal },
    ),
  );
}

function parseDownloadJob(payload: unknown): DownloadJob {
  const result = downloadJobSchema.safeParse(payload);
  if (!result.success) {
    throw new DownloadJobResponseError(result.error.issues);
  }
  return result.data;
}


export async function pauseDownloadJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<DownloadJob> {
  return parseDownloadJob(
    await postJson("/api/download-jobs/" + jobId + "/pause", {}, { signal }),
  );
}

export async function resumeDownloadJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<DownloadJob> {
  return parseDownloadJob(
    await postJson("/api/download-jobs/" + jobId + "/resume", {}, { signal }),
  );
}

export async function cancelDownloadJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<DownloadJob> {
  return parseDownloadJob(
    await postJson("/api/download-jobs/" + jobId + "/cancel", {}, { signal }),
  );
}

export async function deleteDownloadJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<void> {
  await deleteJson("/api/download-jobs/" + jobId, { signal });
}
