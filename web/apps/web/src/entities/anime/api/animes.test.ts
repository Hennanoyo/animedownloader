import { describe, expect, it, vi } from "vitest";
import {
  createAnime,
  createEpisode,
  deleteAnime,
  deleteEpisode,
  getAnime,
  listAnimes,
  updateAnime,
  updateEpisode,
} from "./animes";

const episodePayload = {
  id: "0198a2a8-5b7c-7d7d-8a1f-9f0b8d53f001",
  anime_id: "0198a2a8-5b7c-7d7d-8a1f-9f0b8d53f000",
  episode_number: 1,
  title: "Frieren - 01",
  source: "nyaa",
  source_id: "123456",
  source_title: "[ExampleSubs] Frieren - 01 [1080p].mkv",
  source_url: "https://nyaa.si/view/123456",
  torrent_url: "https://nyaa.si/download/123456.torrent",
  size: "1.24 GiB",
  seeders: 42,
  leechers: 3,
  downloads: 120,
  info_hash: "0123456789abcdef0123456789abcdef01234567",
  download_status: "not_started",
  conversion_status: "not_started",
  created_at: "2026-09-23T00:00:00Z",
  updated_at: "2026-09-23T00:00:00Z",
};

const payload = {
  id: "0198a2a8-5b7c-7d7d-8a1f-9f0b8d53f000",
  title: "Frieren: Beyond Journey's End",
  titles: {
    romaji: "Sousou no Frieren",
    jp: "葬送のフリーレン",
    ko: "장송의 프리렌",
    en: "Frieren: Beyond Journey's End",
  },
  year: 2026,
  season: "fall",
  weekday: "friday",
  air_time: "23:00:00",
  timezone: "Asia/Tokyo",
  created_at: "2026-09-23T00:00:00Z",
  updated_at: "2026-09-23T00:00:00Z",
  episodes: [],
};

describe("anime API", () => {
  it("parses dates from the API", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await createAnime({
      title: payload.title,
      titles: payload.titles,
      year: payload.year,
      season: "fall",
      weekday: "friday",
      air_time: "23:00",
      timezone: "Asia/Tokyo",
      episodes: [],
    });

    expect(result.created_at).toEqual(new Date("2026-09-23T00:00:00Z"));
    vi.unstubAllGlobals();
  });

  it("lists anime records", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify([payload]), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await listAnimes();

    expect(result).toHaveLength(1);
    expect(result[0]?.title).toBe(payload.title);
    vi.unstubAllGlobals();
  });

  it("gets one anime record", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getAnime(payload.id);

    expect(result.id).toBe(payload.id);
    expect(result.episodes).toEqual([]);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/animes/" + payload.id),
      expect.objectContaining({ method: "GET" }),
    );
    vi.unstubAllGlobals();
  });

  it("updates one anime record", async () => {
    const updated = { ...payload, title: "Updated Anime" };
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(updated), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await updateAnime(payload.id, {
      title: "Updated Anime",
      air_time: null,
    });

    expect(result.title).toBe("Updated Anime");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/animes/" + payload.id),
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          title: "Updated Anime",
          air_time: null,
        }),
      }),
    );
    vi.unstubAllGlobals();
  });

  it("deletes one anime record", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(null, { status: 204 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await deleteAnime(payload.id);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/animes/" + payload.id),
      expect.objectContaining({ method: "DELETE" }),
    );
    vi.unstubAllGlobals();
  });

  it("creates an episode", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(episodePayload), { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await createEpisode(payload.id, {
      episode_number: 1,
      title: "Frieren - 01",
      source: "nyaa",
      source_id: "123456",
      source_title: episodePayload.source_title,
      source_url: episodePayload.source_url,
      torrent_url: episodePayload.torrent_url,
      size: episodePayload.size,
      seeders: episodePayload.seeders,
      leechers: episodePayload.leechers,
      downloads: episodePayload.downloads,
      info_hash: episodePayload.info_hash,
    });

    expect(result.id).toBe(episodePayload.id);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/animes/" + payload.id + "/episodes"),
      expect.objectContaining({ method: "POST" }),
    );
    vi.unstubAllGlobals();
  });

  it("updates an episode", async () => {
    const updated = { ...episodePayload, title: "Updated Episode" };
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(updated), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await updateEpisode(episodePayload.id, {
      title: "Updated Episode",
    });

    expect(result.title).toBe("Updated Episode");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/episodes/" + episodePayload.id),
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ title: "Updated Episode" }),
      }),
    );
    vi.unstubAllGlobals();
  });

  it("deletes an episode", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(null, { status: 204 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await deleteEpisode(episodePayload.id);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/episodes/" + episodePayload.id),
      expect.objectContaining({ method: "DELETE" }),
    );
    vi.unstubAllGlobals();
  });
});
