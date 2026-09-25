import { z } from "zod";
import {
  deleteJson,
  getJson,
  patchJson,
  postJson,
} from "../../../shared/api/client";
import type { Anime, CreateAnimeInput, Episode, EpisodeInput } from "../model/types";

const episodeSchema = z.object({
  id: z.uuid(),
  anime_id: z.uuid(),
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

const animeSchema = z.object({
  id: z.uuid(),
  title: z.string(),
  titles: z.record(z.string(), z.string()).default({}),
  year: z.number().int(),
  season: z.enum(["winter", "spring", "summer", "fall"]),
  weekday: z.enum([
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
  ]),
  air_time: z.string().nullable(),
  timezone: z.string(),
  created_at: z.coerce.date(),
  updated_at: z.coerce.date(),
  episodes: z.array(episodeSchema),
});

function formatZodIssues(issues: z.core.$ZodIssue[]): string {
  return issues
    .map((issue) => {
      const path = issue.path.map(String).join(".");
      return path ? path + ": " + issue.message : issue.message;
    })
    .join("; ");
}

export class AnimeResponseError extends Error {
  constructor(readonly issues: z.core.$ZodIssue[]) {
    super(
      "Invalid anime API response: " + formatZodIssues(issues),
    );
    this.name = "AnimeResponseError";
  }
}

export async function listAnimes(signal?: AbortSignal): Promise<Anime[]> {
  const payload = await getJson("/api/animes", { signal });
  return parseList(payload);
}

export async function getAnime(id: string, signal?: AbortSignal): Promise<Anime> {
  return parseAnime(await getJson("/api/animes/" + id, { signal }));
}

export async function createAnime(
  input: CreateAnimeInput,
  signal?: AbortSignal,
): Promise<Anime> {
  return parseAnime(await postJson("/api/animes", input, { signal }));
}

export async function updateAnime(
  id: string,
  input: Partial<Omit<CreateAnimeInput, "episodes">>,
  signal?: AbortSignal,
): Promise<Anime> {
  return parseAnime(await patchJson("/api/animes/" + id, input, { signal }));
}

export async function deleteAnime(id: string, signal?: AbortSignal): Promise<void> {
  await deleteJson("/api/animes/" + id, { signal });
}

export async function createEpisode(
  animeId: string,
  input: EpisodeInput,
  signal?: AbortSignal,
): Promise<Episode> {
  return parseEpisode(
    await postJson("/api/animes/" + animeId + "/episodes", input, { signal }),
  );
}

export async function updateEpisode(
  id: string,
  input: Partial<EpisodeInput>,
  signal?: AbortSignal,
): Promise<Episode> {
  return parseEpisode(await patchJson("/api/episodes/" + id, input, { signal }));
}

export async function deleteEpisode(
  id: string,
  signal?: AbortSignal,
): Promise<void> {
  await deleteJson("/api/episodes/" + id, { signal });
}

function parseList(payload: unknown): Anime[] {
  const result = z.array(animeSchema).safeParse(payload);
  if (!result.success) {
    throw new AnimeResponseError(result.error.issues);
  }
  return result.data;
}

function parseAnime(payload: unknown): Anime {
  const result = animeSchema.safeParse(payload);
  if (!result.success) {
    throw new AnimeResponseError(result.error.issues);
  }
  return result.data;
}

function parseEpisode(payload: unknown): Episode {
  const result = episodeSchema.safeParse(payload);
  if (!result.success) {
    throw new AnimeResponseError(result.error.issues);
  }
  return result.data;
}
