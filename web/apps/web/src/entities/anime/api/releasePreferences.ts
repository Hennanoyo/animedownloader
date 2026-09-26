import { z } from "zod";
import { getJson, patchJson } from "../../../shared/api/client";

const preferenceSchema = z.object({
  release_group_id: z.string().uuid().nullable(),
  resolution: z.string().nullable(),
  video_codec: z.string().nullable(),
  source: z.string().nullable(),
  created_at: z.coerce.date(),
  updated_at: z.coerce.date(),
});

export type AnimeReleasePreference = z.infer<typeof preferenceSchema>;
export type AnimeReleasePreferenceInput = {
  release_group_id: string | null;
  resolution: string | null;
  video_codec: string | null;
  source: string | null;
};

export class AnimeReleasePreferenceResponseError extends Error {
  constructor(readonly issues: z.core.$ZodIssue[]) {
    super(
      "Invalid anime release preference response: " +
        issues.map((issue) => issue.message).join("; "),
    );
    this.name = "AnimeReleasePreferenceResponseError";
  }
}

export async function getAnimeReleasePreference(
  animeId: string,
  signal?: AbortSignal,
): Promise<AnimeReleasePreference | null> {
  const payload = await getJson(
    "/api/animes/" + animeId + "/release-preferences",
    { signal },
  );
  if (payload === null) return null;

  const result = preferenceSchema.safeParse(payload);
  if (!result.success) {
    throw new AnimeReleasePreferenceResponseError(result.error.issues);
  }
  return result.data;
}

export async function updateAnimeReleasePreference(
  animeId: string,
  input: AnimeReleasePreferenceInput,
  signal?: AbortSignal,
): Promise<AnimeReleasePreference> {
  const payload = await patchJson(
    "/api/animes/" + animeId + "/release-preferences",
    input,
    { signal },
  );
  const result = preferenceSchema.safeParse(payload);
  if (!result.success) {
    throw new AnimeReleasePreferenceResponseError(result.error.issues);
  }
  return result.data;
}
