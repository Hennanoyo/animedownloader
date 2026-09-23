import { describe, expect, it, vi } from "vitest";
import {
  createAnime,
  deleteAnime,
  getAnime,
  listAnimes,
  updateAnime,
} from "./animes";

const payload = {
  id: "0198a2a8-5b7c-7d7d-8a1f-9f0b8d53f000",
  title: "Frieren: Beyond Journey's End",
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
});
