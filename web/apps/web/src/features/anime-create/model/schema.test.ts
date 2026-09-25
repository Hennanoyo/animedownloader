import { describe, expect, it } from "vitest";
import { animeCreateFormSchema } from "./schema";

const release = {
  source: "nyaa",
  id: "https://nyaa.si/view/123456",
  title: "[ExampleSubs] Frieren - 01 [1080p].mkv",
  page_url: "https://nyaa.si/view/123456",
  torrent_url: "https://nyaa.si/download/123456.torrent",
  published_at: new Date("2026-09-22T10:20:30Z"),
  size: "1.24 GiB",
  seeders: 42,
  leechers: 3,
  downloads: 120,
  info_hash: "0123456789abcdef0123456789abcdef01234567",
};

const base = {
  title: "Frieren",
  titles: {
    romaji: "Sousou no Frieren",
    jp: "葬送のフリーレン",
    ko: "장송의 프리렌",
    en: "Frieren: Beyond Journey's End",
  },
  year: 2026,
  season: "fall" as const,
  weekday: "friday" as const,
  air_time: "23:00",
  timezone: "Asia/Tokyo",
  episodes: [
    {
      episode_number: 1,
      title: "Frieren - 01",
      release,
    },
  ],
};

describe("anime create form schema", () => {
  it("accepts a complete anime", () => {
    expect(animeCreateFormSchema.safeParse(base).success).toBe(true);
  });

  it("requires a release", () => {
    const result = animeCreateFormSchema.safeParse({
      ...base,
      episodes: [{ ...base.episodes[0], release: null }],
    });

    expect(result.success).toBe(false);
  });

  it("rejects duplicate episode numbers", () => {
    const result = animeCreateFormSchema.safeParse({
      ...base,
      episodes: [
        base.episodes[0],
        { ...base.episodes[0], title: "Duplicate" },
      ],
    });

    expect(result.success).toBe(false);
  });
});
