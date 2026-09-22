import { z } from "zod";
import { getJson } from "../../../shared/api/client";
import type { ReleaseSearchResponse } from "../model/types";

const releaseSchema = z.object({
  source: z.string(),
  id: z.string(),
  title: z.string(),
  page_url: z.string().url(),
  torrent_url: z.string().url(),
  published_at: z.iso.datetime({ offset: true }).nullable(),
  size: z.string().nullable(),
  seeders: z.number().int().nonnegative().nullable(),
  leechers: z.number().int().nonnegative().nullable(),
  downloads: z.number().int().nonnegative().nullable(),
  info_hash: z.string().nullable(),
});

const responseSchema = z.object({
  query: z.string(),
  items: z.array(releaseSchema),
});

export async function searchReleases(
  query: string,
  signal?: AbortSignal,
): Promise<ReleaseSearchResponse> {
  const params = new URLSearchParams({ q: query });
  const payload = await getJson(
    "/api/releases/search?" + params.toString(),
    { signal },
  );
  return responseSchema.parse(payload);
}
