import { z } from "zod";
import { candidateSchema } from "../../release/api/discoveryCandidates";
import { getJson, patchJson, postJson } from "../../../shared/api/client";

const policySchema = z.object({
  anime_id: z.uuid(),
  enabled: z.boolean(),
  mode: z.enum(["off", "accept", "download"]),
  min_ranking_score: z.number().int().min(0).max(160),
  require_preference_match: z.boolean(),
  created_at: z.coerce.date().nullable(),
  updated_at: z.coerce.date().nullable(),
});

const previewSchema = z.object({
  candidate: candidateSchema,
  eligible: z.boolean(),
  reasons: z.array(z.string()),
  automation_status: z.string(),
});

const runSchema = z.object({
  anime_id: z.uuid(),
  status: z.string(),
});

export type ReleaseAutomationPolicy = z.infer<typeof policySchema>;
export type ReleaseAutomationPolicyInput = {
  mode: "off" | "accept" | "download";
  min_ranking_score: number;
  require_preference_match: boolean;
};
export type ReleaseAutomationPreview = z.infer<typeof previewSchema>;
export type ReleaseAutomationRun = z.infer<typeof runSchema>;

export async function getReleaseAutomationPolicy(
  animeId: string,
  signal?: AbortSignal,
): Promise<ReleaseAutomationPolicy> {
  const result = policySchema.safeParse(
    await getJson("/api/animes/" + animeId + "/release-automation-policy", {
      signal,
    }),
  );
  if (!result.success) {
    throw new Error("Invalid release automation policy response");
  }
  return result.data;
}

export async function updateReleaseAutomationPolicy(
  animeId: string,
  input: ReleaseAutomationPolicyInput,
  signal?: AbortSignal,
): Promise<ReleaseAutomationPolicy> {
  const result = policySchema.safeParse(
    await patchJson(
      "/api/animes/" + animeId + "/release-automation-policy",
      input,
      { signal },
    ),
  );
  if (!result.success) {
    throw new Error("Invalid release automation policy response");
  }
  return result.data;
}

export async function previewReleaseAutomation(
  animeId: string,
  signal?: AbortSignal,
): Promise<ReleaseAutomationPreview[]> {
  const result = z.array(previewSchema).safeParse(
    await getJson("/api/animes/" + animeId + "/release-automation-preview", {
      signal,
    }),
  );
  if (!result.success) {
    throw new Error("Invalid release automation preview response");
  }
  return result.data;
}

export async function runReleaseAutomation(
  animeId: string,
  signal?: AbortSignal,
): Promise<ReleaseAutomationRun> {
  const result = runSchema.safeParse(
    await postJson(
      "/api/animes/" + animeId + "/release-automation/run",
      {},
      { signal },
    ),
  );
  if (!result.success) {
    throw new Error("Invalid release automation run response");
  }
  return result.data;
}

