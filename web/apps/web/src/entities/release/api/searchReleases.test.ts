import { describe, expect, it, vi } from "vitest";
import { searchReleases } from "./searchReleases";

const validRelease = {
  source: "nyaa",
  id: "https://nyaa.si/view/123456",
  title: "[ExampleSubs] Frieren - 01 [1080p].mkv",
  page_url: "https://nyaa.si/view/123456",
  torrent_url: "https://nyaa.si/download/123456.torrent",
  published_at: "2026-09-22T10:20:30+00:00",
  size: "1.24 GiB",
  seeders: 42,
  leechers: 3,
  downloads: 120,
  info_hash: "0123456789abcdef0123456789abcdef01234567",
};

describe("searchReleases", () => {
  it("parses a valid API response with an offset-aware timestamp", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          query: "Frieren",
          items: [validRelease],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await searchReleases("Frieren");

    expect(result.query).toBe("Frieren");
    expect(result.items).toHaveLength(1);
    expect(result.items[0].seeders).toBe(42);
    expect(result.items[0].published_at).toEqual(new Date("2026-09-22T10:20:30+00:00"));
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/releases/search?q=Frieren",
      expect.objectContaining({ method: "GET" }),
    );

    vi.unstubAllGlobals();
  });

  it("reports the exact field when response validation fails", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          query: "Frieren",
          items: [{ ...validRelease, seeders: "42" }],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(searchReleases("Frieren")).rejects.toMatchObject({
      name: "ReleaseSearchResponseError",
      message: expect.stringContaining("items.0.seeders"),
    });

    vi.unstubAllGlobals();
  });

  it("propagates API failures with their status", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Nyaa search is temporarily unavailable" }),
        { status: 502 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(searchReleases("Frieren")).rejects.toMatchObject({
      name: "ApiRequestError",
      status: 502,
      message:
        "API request failed with status 502: Nyaa search is temporarily unavailable",
    });

    vi.unstubAllGlobals();
  });

  it("passes the abort signal to fetch", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ query: "Frieren", items: [] }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await searchReleases("Frieren", controller.signal);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/releases/search?q=Frieren",
      expect.objectContaining({ signal: controller.signal }),
    );

    vi.unstubAllGlobals();
  });
});
