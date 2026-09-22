import { describe, expect, it, vi } from "vitest";
import { searchReleases } from "./searchReleases";

describe("searchReleases", () => {
  it("parses a valid API response with an offset-aware timestamp", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          query: "Frieren",
          items: [
            {
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
            },
          ],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await searchReleases("Frieren");

    expect(result.query).toBe("Frieren");
    expect(result.items).toHaveLength(1);
    expect(result.items[0].seeders).toBe(42);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    vi.unstubAllGlobals();
  });
});
