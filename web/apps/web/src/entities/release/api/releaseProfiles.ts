import { z } from "zod";

export const parserFields = [
  "release_group",
  "series_title",
  "episode_number",
  "episode_title",
  "season_number",
  "resolution",
  "source",
  "video_codec",
  "audio_codec",
  "bit_depth",
] as const;
import {
  deleteJson,
  getJson,
  patchJson,
  postJson,
} from "../../../shared/api/client";

const releaseGroupSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  slug: z.string(),
  enabled: z.boolean(),
  active_parser_profile_version: z.number().int().positive().nullable(),
  draft_parser_profile_version: z.number().int().positive().nullable(),
});

const parserRuleSchema = z.object({
  id: z.uuid(),
  field: z.enum(parserFields),
  pattern: z.string(),
  priority: z.number().int(),
  required: z.boolean(),
  flags: z.string(),
  transform: z.enum([
    "identity",
    "strip",
    "normalize_spaces",
    "to_int",
    "lower",
    "upper",
  ]),
});

const parserProfileSchema = z.object({
  id: z.uuid(),
  release_group_id: z.uuid(),
  release_group_name: z.string(),
  version: z.number().int().positive(),
  status: z.enum(["draft", "active", "retired"]),
  created_at: z.coerce.date(),
  activated_at: z.coerce.date().nullable(),
  rules: z.array(parserRuleSchema),
});

const sampleSchema = z.object({
  id: z.uuid(),
  release_group_id: z.uuid(),
  source: z.string(),
  title: z.string(),
  created_at: z.coerce.date(),
  updated_at: z.coerce.date(),
});

const observationSchema = z.object({
  id: z.uuid(),
  release_group_id: z.uuid(),
  profile_id: z.uuid(),
  source: z.string(),
  title: z.string(),
  status: z.string(),
  failed_required_fields: z.array(z.string()),
  observed_at: z.coerce.date(),
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

const validationSchema = z.object({
  valid: z.boolean(),
  sample_count: z.number().int().nonnegative(),
  minimum_samples: z.number().int().positive(),
  errors: z.array(z.string()),
  results: z.array(
    z.object({
      sample_id: z.uuid(),
      title: z.string(),
      parsed: parsedReleaseSchema.nullable(),
      error: z.string().nullable(),
    }),
  ),
});

const comparisonSchema = z.object({
  profile_id: z.uuid(),
  draft_version: z.number().int().positive(),
  active_version: z.number().int().positive().nullable(),
  differences: z.array(
    z.object({
      sample_id: z.uuid(),
      title: z.string(),
      fields: z.record(z.string(), z.array(z.unknown())),
    }),
  ),
});

const healthSchema = z.object({
  profile_id: z.uuid(),
  total_count: z.number().int().nonnegative(),
  parsed_count: z.number().int().nonnegative(),
  ambiguous_count: z.number().int().nonnegative(),
  unparsed_count: z.number().int().nonnegative(),
  unsupported_count: z.number().int().nonnegative(),
  failure_rate: z.number().min(0).max(1),
  drift_signal: z.boolean(),
  drift_reason: z.string().nullable(),
  recent_failures: z.array(observationSchema),
});

export type ReleaseGroupSummary = z.infer<typeof releaseGroupSchema>;
export type ParserRule = z.infer<typeof parserRuleSchema>;
export type ParserProfile = z.infer<typeof parserProfileSchema>;
export type ParserSample = z.infer<typeof sampleSchema>;
export type ParserObservation = z.infer<typeof observationSchema>;
export type ParserValidation = z.infer<typeof validationSchema>;
export type ParserComparison = z.infer<typeof comparisonSchema>;
export type ParserHealth = z.infer<typeof healthSchema>;

export type ParserRuleInput = Omit<ParserRule, "id">;

export class ReleaseProfileResponseError extends Error {
  constructor(readonly issues: z.core.$ZodIssue[]) {
    super(
      "Invalid release profile API response: " +
        issues
          .map(
            (issue) =>
              (issue.path.join(".") || "<root>") + ": " + issue.message,
          )
          .join("; "),
    );
    this.name = "ReleaseProfileResponseError";
  }
}

export async function createReleaseGroup(
  input: { name: string; slug?: string },
  signal?: AbortSignal,
): Promise<ReleaseGroupSummary> {
  return parseSchema(
    await postJson("/api/release-groups", input, { signal }),
    releaseGroupSchema,
  );
}

export async function getReleaseGroups(
  signal?: AbortSignal,
): Promise<ReleaseGroupSummary[]> {
  return parseList(await getJson("/api/release-groups", { signal }), releaseGroupSchema);
}

export async function getParserProfiles(
  groupId: string,
  signal?: AbortSignal,
): Promise<ParserProfile[]> {
  return parseList(
    await getJson("/api/release-groups/" + groupId + "/parser-profiles", { signal }),
    parserProfileSchema,
  );
}

export async function createParserDraft(
  groupId: string,
  signal?: AbortSignal,
): Promise<ParserProfile> {
  return parseParserProfile(
    await postJson("/api/release-groups/" + groupId + "/parser-profiles/drafts", {}, { signal }),
  );
}

export async function updateParserProfile(
  profileId: string,
  rules: ParserRuleInput[],
  signal?: AbortSignal,
): Promise<ParserProfile> {
  return parseParserProfile(
    await patchJson(
      "/api/release-parser-profiles/" + profileId,
      { rules },
      { signal },
    ),
  );
}

export async function getParserSamples(
  groupId: string,
  signal?: AbortSignal,
): Promise<ParserSample[]> {
  return parseList(
    await getJson("/api/release-groups/" + groupId + "/parser-samples", { signal }),
    sampleSchema,
  );
}

export async function createParserSample(
  groupId: string,
  input: { title: string; source: string },
  signal?: AbortSignal,
): Promise<ParserSample> {
  return parseSchema(
    await postJson("/api/release-groups/" + groupId + "/parser-samples", input, { signal }),
    sampleSchema,
  );
}

export async function deleteParserSample(
  sampleId: string,
  signal?: AbortSignal,
): Promise<void> {
  await deleteJson("/api/release-parser-samples/" + sampleId, { signal });
}

export async function validateParserProfile(
  profileId: string,
  signal?: AbortSignal,
): Promise<ParserValidation> {
  return parseSchema(
    await postJson("/api/release-parser-profiles/" + profileId + "/validate", {}, { signal }),
    validationSchema,
  );
}

export async function compareParserProfile(
  profileId: string,
  signal?: AbortSignal,
): Promise<ParserComparison> {
  return parseSchema(
    await getJson("/api/release-parser-profiles/" + profileId + "/comparison", { signal }),
    comparisonSchema,
  );
}

export async function getParserHealth(
  profileId: string,
  signal?: AbortSignal,
): Promise<ParserHealth> {
  return parseSchema(
    await getJson("/api/release-parser-profiles/" + profileId + "/health", { signal }),
    healthSchema,
  );
}

export async function activateParserProfile(
  profileId: string,
  signal?: AbortSignal,
): Promise<ParserProfile> {
  return parseParserProfile(
    await postJson("/api/release-parser-profiles/" + profileId + "/activate", {}, { signal }),
  );
}

export async function createDraftFromObservation(
  observationId: string,
  signal?: AbortSignal,
): Promise<ParserProfile> {
  return parseParserProfile(
    await postJson(
      "/api/release-parser-observations/" + observationId + "/draft",
      {},
      { signal },
    ),
  );
}

function parseParserProfile(payload: unknown): ParserProfile {
  return parseSchema(payload, parserProfileSchema);
}

function parseSchema<T extends z.ZodType>(
  payload: unknown,
  schema: T,
): z.infer<T> {
  const result = schema.safeParse(payload);
  if (!result.success) {
    throw new ReleaseProfileResponseError(result.error.issues);
  }
  return result.data;
}

function parseList<T extends z.ZodType>(
  payload: unknown,
  schema: T,
): z.infer<T>[] {
  return parseSchema(payload, z.array(schema));
}
