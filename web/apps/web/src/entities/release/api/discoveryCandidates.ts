import { z } from "zod";
import { formatZodIssues } from "../../../shared/lib/validation";
import { getJson, patchJson, postJson } from "../../../shared/api/client";

export const releaseCandidateStatuses = [
  "new",
  "reviewed",
  "accepted",
  "rejected",
  "stale",
] as const;

export type ReleaseCandidateStatus = (typeof releaseCandidateStatuses)[number];

const matchCandidateSchema = z.object({
  anime_id: z.uuid(),
  title: z.string(),
  matched_titles: z.array(z.string()),
});

export const candidateSchema = z.object({
  id: z.uuid(),
  anime_id: z.uuid(),
  last_run_id: z.uuid().nullable(),
  provider_source: z.string(),
  source_id: z.string(),
  source_title: z.string(),
  page_url: z.string().url(),
  torrent_url: z.string().url(),
  published_at: z.coerce.date().nullable(),
  size: z.string().nullable(),
  seeders: z.number().int().nonnegative().nullable(),
  leechers: z.number().int().nonnegative().nullable(),
  downloads: z.number().int().nonnegative().nullable(),
  info_hash: z.string().nullable(),
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
  parse_status: z.string(),
  parse_warnings: z.array(z.string()),
  failed_required_fields: z.array(z.string()),
  parser_profile_version: z.number().int().positive().nullable(),
  normalized_series_title: z.string().nullable(),
  match_status: z.string(),
  match_candidates: z.array(matchCandidateSchema),
  ranking_score: z.number().int().nonnegative(),
  ranking_reasons: z.array(z.string()),
  status: z.enum(releaseCandidateStatuses),
  first_seen_at: z.coerce.date(),
  last_seen_at: z.coerce.date(),
  reviewed_at: z.coerce.date().nullable(),
  automation_status: z.enum(["idle", "claimed", "completed", "blocked"]),
  automation_claimed_at: z.coerce.date().nullable(),
  automation_completed_at: z.coerce.date().nullable(),
  automation_error: z.string().nullable(),
});

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
  download_status: z.string(),
  conversion_status: z.string(),
  created_at: z.coerce.date(),
  updated_at: z.coerce.date(),
});

const acceptanceSchema = z.object({
  status: z.enum(["created", "idempotent", "replacement_candidate", "replaced"]),
  candidate: candidateSchema,
  episode: episodeSchema.nullable(),
  existing_episode: episodeSchema.nullable(),
});

const runQuerySchema = z.object({
  id: z.uuid(),
  position: z.number().int().positive(),
  query: z.string(),
  status: z.string(),
  result_count: z.number().int().nonnegative(),
  result_cap_reached: z.boolean(),
  error_message: z.string().nullable(),
  created_at: z.coerce.date(),
});


const runSchema = z.object({
  id: z.uuid(),
  anime_id: z.uuid(),
  scheduled_for: z.coerce.date(),
  status: z.string(),
  query: z.string().nullable(),
  search_profile_version: z.number().int().positive().nullable(),
  candidate_count: z.number().int().nonnegative(),
  warning_count: z.number().int().nonnegative(),
  error_message: z.string().nullable(),
  started_at: z.coerce.date().nullable(),
  completed_at: z.coerce.date().nullable(),
  created_at: z.coerce.date(),
  queries: z.array(runQuerySchema),
});

const searchPlanQuerySchema = z.object({
  position: z.number().int().positive(),
  query: z.string(),
  fields: z.array(z.string()),
});

const searchPlanSchema = z.object({
  anime_id: z.uuid(),
  query_budget: z.number().int().positive(),
  search_profile_version: z.number().int().positive().nullable(),
  queries: z.array(searchPlanQuerySchema).min(1),
});

const scheduleSchema = z.object({
  anime_id: z.uuid(),
  enabled: z.boolean(),
  interval_minutes: z.number().int().min(15).max(1440),
  next_run_at: z.coerce.date().nullable(),
  last_run_at: z.coerce.date().nullable(),
  last_run_status: z.string().nullable(),
});

export type ReleaseDiscoveryCandidate = z.infer<typeof candidateSchema>;
export type ReleaseDiscoveryCandidateAcceptance = z.infer<typeof acceptanceSchema>;
export type ReleaseDiscoveryRun = z.infer<typeof runSchema>;
export type ReleaseDiscoverySchedule = z.infer<typeof scheduleSchema>;
export type ReleaseDiscoverySearchPlan = z.infer<typeof searchPlanSchema>;

export class ReleaseDiscoveryCandidateResponseError extends Error {
  constructor(readonly issues: z.core.$ZodIssue[]) {
    super("Invalid release discovery candidate API response: " + formatZodIssues(issues));
    this.name = "ReleaseDiscoveryCandidateResponseError";
  }
}

export async function listReleaseDiscoveryCandidates(
  params: { animeId?: string; status?: ReleaseCandidateStatus; limit?: number },
  signal?: AbortSignal,
): Promise<ReleaseDiscoveryCandidate[]> {
  const query = new URLSearchParams();
  if (params.animeId) query.set("anime_id", params.animeId);
  if (params.status) query.set("status", params.status);
  if (params.limit) query.set("limit", String(params.limit));
  const payload = await getJson(
    "/api/release-discovery/candidates?" + query.toString(),
    { signal },
  );
  const result = z.array(candidateSchema).safeParse(payload);
  if (!result.success) throw new ReleaseDiscoveryCandidateResponseError(result.error.issues);
  return result.data;
}

export async function updateReleaseDiscoveryCandidate(
  candidateId: string,
  status: Exclude<ReleaseCandidateStatus, "accepted">,
  signal?: AbortSignal,
): Promise<ReleaseDiscoveryCandidate> {
  const payload = await patchJson(
    "/api/release-discovery/candidates/" + candidateId,
    { status },
    { signal },
  );
  const result = candidateSchema.safeParse(payload);
  if (!result.success) throw new ReleaseDiscoveryCandidateResponseError(result.error.issues);
  return result.data;
}

export async function acceptReleaseDiscoveryCandidate(
  candidateId: string,
  replaceEpisodeId?: string,
  signal?: AbortSignal,
): Promise<ReleaseDiscoveryCandidateAcceptance> {
  const payload = await postJson(
    "/api/release-discovery/candidates/" + candidateId + "/accept",
    { replace_episode_id: replaceEpisodeId ?? null },
    { signal },
  );
  const result = acceptanceSchema.safeParse(payload);
  if (!result.success) throw new ReleaseDiscoveryCandidateResponseError(result.error.issues);
  return result.data;
}

export async function listReleaseDiscoveryRuns(
  animeId?: string,
  signal?: AbortSignal,
): Promise<ReleaseDiscoveryRun[]> {
  const query = new URLSearchParams();
  if (animeId) query.set("anime_id", animeId);
  const payload = await getJson(
    "/api/release-discovery/runs?" + query.toString(),
    { signal },
  );
  const result = z.array(runSchema).safeParse(payload);
  if (!result.success) throw new ReleaseDiscoveryCandidateResponseError(result.error.issues);
  return result.data;
}

export async function getReleaseDiscoverySearchPlan(
  animeId: string,
  signal?: AbortSignal,
): Promise<ReleaseDiscoverySearchPlan> {
  const payload = await getJson(
    "/api/animes/" + animeId + "/release-discovery/plan",
    { signal },
  );
  const result = searchPlanSchema.safeParse(payload);
  if (!result.success) {
    throw new ReleaseDiscoveryCandidateResponseError(result.error.issues);
  }
  return result.data;
}

export async function getReleaseDiscoverySchedule(
  animeId: string,
  signal?: AbortSignal,
): Promise<ReleaseDiscoverySchedule> {
  const payload = await getJson(
    "/api/animes/" + animeId + "/release-discovery-schedule",
    { signal },
  );
  const result = scheduleSchema.safeParse(payload);
  if (!result.success) throw new ReleaseDiscoveryCandidateResponseError(result.error.issues);
  return result.data;
}

export async function updateReleaseDiscoverySchedule(
  animeId: string,
  input: { enabled: boolean; interval_minutes: number },
  signal?: AbortSignal,
): Promise<ReleaseDiscoverySchedule> {
  const payload = await patchJson(
    "/api/animes/" + animeId + "/release-discovery-schedule",
    input,
    { signal },
  );
  const result = scheduleSchema.safeParse(payload);
  if (!result.success) throw new ReleaseDiscoveryCandidateResponseError(result.error.issues);
  return result.data;
}

export async function runReleaseDiscoveryNow(
  animeId: string,
  signal?: AbortSignal,
): Promise<ReleaseDiscoveryRun> {
  const payload = await postJson(
    "/api/animes/" + animeId + "/release-discovery/run",
    {},
    { signal },
  );
  const result = runSchema.safeParse(payload);
  if (!result.success) throw new ReleaseDiscoveryCandidateResponseError(result.error.issues);
  return result.data;
}
