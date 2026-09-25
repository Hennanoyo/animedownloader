import { expect, test } from "@playwright/test";

const ANIME_ID = "019a0000-0000-7000-8000-000000000120";
const EPISODE_ID = "019a0000-0000-7000-8000-000000000121";

const release = {
  id: "e2e-create-release-1",
  source: "nyaa",
  title: "[ExampleSubs] Browser Create Anime - 01 [1080p][HEVC]",
  page_url: "https://e2e.invalid/release/create-1",
  torrent_url: "https://e2e.invalid/download/create-1.torrent",
  published_at: "2026-09-25T00:00:00Z",
  size: "1 GiB",
  seeders: 15,
  leechers: 1,
  downloads: 20,
  info_hash: "cccccccccccccccccccccccccccccccccccccccc",
};

const createdAnime = {
  id: ANIME_ID,
  title: "Browser Create Anime",
  titles: {
    romaji: "Burauza Kurieito Anime",
    jp: "ブラウザクリエイトアニメ",
    ko: "브라우저 생성 애니",
    en: "Browser Create Anime",
  },
  year: 2026,
  season: "fall",
  weekday: "friday",
  air_time: "23:00:00",
  timezone: "Asia/Tokyo",
  created_at: "2026-09-25T00:00:00Z",
  updated_at: "2026-09-25T00:00:00Z",
  episodes: [
    {
      id: EPISODE_ID,
      anime_id: ANIME_ID,
      episode_number: 1,
      title: release.title,
      source: "nyaa",
      source_id: release.id,
      source_title: release.title,
      source_url: release.page_url,
      torrent_url: release.torrent_url,
      size: release.size,
      seeders: release.seeders,
      leechers: release.leechers,
      downloads: release.downloads,
      info_hash: release.info_hash,
      download_status: "not_started",
      conversion_status: "not_started",
      created_at: "2026-09-25T00:00:00Z",
      updated_at: "2026-09-25T00:00:00Z",
    },
  ],
};

test("creates an Anime after all required fields and a release are selected", async ({
  page,
}) => {
  await page.route("**/api/releases/search?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        query: "Browser Create Anime 01",
        items: [release],
      }),
    });
  });

  await page.route("**/api/animes", async (route) => {
    if (route.request().method() === "POST") {
      const body = JSON.parse(route.request().postData() ?? "{}") as {
        title?: string;
        year?: number;
        season?: string;
        weekday?: string;
        air_time?: string | null;
        timezone?: string;
        episodes?: Array<{
          episode_number?: number;
          title?: string;
          source_id?: string;
        }>;
      };

      expect(body.title).toBe("Browser Create Anime");
      expect(body.year).toBe(2026);
      expect(body.season).toBe("fall");
      expect(body.weekday).toBe("friday");
      expect(body.air_time).toBe("23:00");
      expect(body.timezone).toBe("Asia/Tokyo");
      expect(body.episodes?.[0]?.episode_number).toBe(1);
      expect(body.episodes?.[0]?.title).toBe(release.title);
      expect(body.episodes?.[0]?.source_id).toBe(release.id);

      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(createdAnime),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([createdAnime]),
    });
  });

  await page.goto("/animes/new");

  await page.getByLabel("Title", { exact: true }).fill("Browser Create Anime");
  await page.getByLabel("Romaji title", { exact: true }).fill("Burauza Kurieito Anime");
  await page.getByLabel("Japanese title", { exact: true }).fill("ブラウザクリエイトアニメ");
  await page.getByLabel("Korean title", { exact: true }).fill("브라우저 생성 애니");
  await page.getByLabel("English title", { exact: true }).fill("Browser Create Anime");
  await page.getByLabel("Year", { exact: true }).fill("2026");
  await page.getByRole("button", { name: "Fall" }).click();
  await page.getByRole("option", { name: "Fall" }).click();
  await page.getByRole("button", { name: "Friday" }).click();
  await page.getByRole("option", { name: "Friday" }).click();
  await page.getByLabel("Air time", { exact: true }).fill("23:00");
  await page.getByLabel("Timezone", { exact: true }).fill("Asia/Tokyo");

  await page.getByRole("button", { name: "Add episode" }).click();
  await page.getByLabel("Search Nyaa releases", { exact: true }).fill("Browser Create Anime 01");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page.getByRole("button", { name: "Select" })).toBeVisible();
  await page.getByRole("button", { name: "Select" }).click();

  await page.getByRole("button", { name: "Create anime" }).click();

  await expect(
    page.getByRole("heading", { name: "Anime", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Browser Create Anime", exact: true }),
  ).toBeVisible();
});

test("creates an Anime without episodes when none have been added", async ({
  page,
}) => {
  let createRequests = 0;

  await page.route("**/api/animes", async (route) => {
    if (route.request().method() === "POST") {
      createRequests += 1;
      const body = JSON.parse(route.request().postData() ?? "{}") as {
        episodes?: unknown[];
      };

      expect(body.episodes).toEqual([]);

      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          ...createdAnime,
          title: "Anime Without Episodes",
          episodes: [],
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.goto("/animes/new");

  await page.getByLabel("Title", { exact: true }).fill("Anime Without Episodes");
  await page.getByLabel("Year", { exact: true }).fill("2026");
  await page.getByLabel("Air time", { exact: true }).fill("23:00");
  await page.getByLabel("Timezone", { exact: true }).fill("Asia/Tokyo");

  await page.getByRole("button", { name: "Create anime" }).click();

  await expect(
    page.getByRole("heading", { name: "Anime", exact: true }),
  ).toBeVisible();
  await expect.poll(() => createRequests).toBe(1);
});

test("can add and remove an episode before creating an Anime", async ({
  page,
}) => {
  await page.goto("/animes/new");

  await expect(page.getByText("No episodes added yet.")).toBeVisible();

  await page.getByRole("button", { name: "Add episode" }).click();
  await expect(page.getByText("Episode 1", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Remove" }).click();

  await expect(page.getByText("No episodes added yet.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Remove" })).toHaveCount(0);
});

test("shows actionable validation feedback when an episode release is missing", async ({
  page,
}) => {
  await page.goto("/animes/new");

  await page.getByLabel("Title", { exact: true }).fill("Validation Anime");
  await page.getByLabel("Year", { exact: true }).fill("2026");
  await page.getByLabel("Air time", { exact: true }).fill("23:00");
  await page.getByLabel("Timezone", { exact: true }).fill("Asia/Tokyo");

  await page.getByRole("button", { name: "Add episode" }).click();
  await page.getByRole("button", { name: "Create anime" }).click();

  await expect(page.getByRole("alert")).toContainText(
    "Select a Nyaa release.",
  );
});
