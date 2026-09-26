import { expect, test } from "@playwright/test";

const ANIME_ID = "019a0000-0000-7000-8000-000000000020";
const CANDIDATE_ID = "019a0000-0000-7000-8000-000000000021";
const RUN_ID = "019a0000-0000-7000-8000-000000000022";

const anime = {
  id: ANIME_ID,
  title: "Candidate Inbox Anime",
  titles: { romaji: "Candidate Inbox Anime" },
  year: 2026,
  season: "fall",
  weekday: "friday",
  air_time: null,
  timezone: "Asia/Tokyo",
  created_at: "2026-09-26T00:00:00Z",
  updated_at: "2026-09-26T00:00:00Z",
  episodes: [],
};

let candidateStatus: "new" | "reviewed" | "rejected" | "stale" = "new";
let schedule = {
  anime_id: ANIME_ID,
  enabled: false,
  interval_minutes: 360,
  next_run_at: null as string | null,
  last_run_at: null as string | null,
  last_run_status: null as string | null,
};

const candidate = () => ({
  id: CANDIDATE_ID,
  anime_id: ANIME_ID,
  last_run_id: RUN_ID,
  provider_source: "nyaa",
  source_id: "123456",
  source_title: "[ExampleSubs] Candidate Inbox Anime - 01 [1080p][HEVC]",
  page_url: "https://e2e.invalid/release/123456",
  torrent_url: "https://e2e.invalid/download/123456.torrent",
  published_at: "2026-09-26T00:00:00Z",
  size: "1 GiB",
  seeders: 18,
  leechers: 2,
  downloads: 30,
  info_hash: "abcdef0123456789abcdef0123456789abcdef01",
  normalized_title: "[ExampleSubs] Candidate Inbox Anime - 01 [1080p][HEVC]",
  release_group: "ExampleSubs",
  series_title: "Candidate Inbox Anime",
  episode_number: 1,
  episode_title: null,
  season_number: null,
  resolution: "1080p",
  source: "WEB",
  video_codec: "HEVC",
  audio_codec: "AAC",
  bit_depth: 10,
  parse_status: "parsed",
  parse_warnings: [],
  failed_required_fields: [],
  parser_profile_version: 1,
  normalized_series_title: "candidate inbox anime",
  match_status: "matched",
  match_candidates: [
    {
      anime_id: ANIME_ID,
      title: "Candidate Inbox Anime",
      matched_titles: ["Candidate Inbox Anime"],
    },
  ],
  ranking_score: 160,
  ranking_reasons: [
    "Preferred release group",
    "Preferred resolution",
    "Preferred video codec",
    "Preferred source",
  ],
  status: candidateStatus,
  first_seen_at: "2026-09-26T00:00:00Z",
  last_seen_at: "2026-09-26T00:05:00Z",
  reviewed_at:
    candidateStatus === "new" ? null : "2026-09-26T00:06:00Z",
});

test.beforeEach(async ({ page }) => {
  candidateStatus = "new";
  schedule = {
    anime_id: ANIME_ID,
    enabled: false,
    interval_minutes: 360,
    next_run_at: null,
    last_run_at: null,
    last_run_status: null,
  };

  await page.route("**/api/animes", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([anime]),
    });
  });
  await page.route("**/api/release-discovery/candidates**", async (route) => {
    if (route.request().method() === "PATCH") {
      const body = JSON.parse(route.request().postData() ?? "{}") as {
        status?: typeof candidateStatus;
      };
      candidateStatus = body.status ?? candidateStatus;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(candidate()),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([candidate()]),
    });
  });
  await page.route("**/api/release-discovery/runs**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: RUN_ID,
          anime_id: ANIME_ID,
          scheduled_for: "2026-09-26T00:00:00Z",
          status: "completed",
          query: "Candidate Inbox Anime",
          search_profile_version: null,
          candidate_count: 1,
          warning_count: 0,
          error_message: null,
          started_at: "2026-09-26T00:00:01Z",
          completed_at: "2026-09-26T00:00:05Z",
          created_at: "2026-09-26T00:00:00Z",
        },
      ]),
    });
  });
});

test("reviews a persisted discovery candidate in the inbox", async ({ page }) => {
  await page.goto("/release-inbox");

  await expect(
    page.getByRole("heading", { name: "Candidate inbox" }),
  ).toBeVisible();
  await expect(page.getByText("Candidate Inbox Anime", { exact: true })).toHaveCount(2);
  await expect(
    page.getByRole("heading", {
      name: "[ExampleSubs] Candidate Inbox Anime - 01 [1080p][HEVC]",
    }),
  ).toBeVisible();

  const card = page.locator("article").filter({
    hasText: "[ExampleSubs] Candidate Inbox Anime - 01 [1080p][HEVC]",
  });
  await expect(card).toContainText("Preferred 160");
  await expect(card).toContainText(
    "Preferred release group · Preferred resolution · Preferred video codec · Preferred source",
  );

  await card.getByRole("button", { name: "Mark reviewed" }).click();
  await expect(card.getByText("reviewed", { exact: true })).toBeVisible();
  await expect(
    card.getByRole("button", { name: "Mark reviewed" }),
  ).toHaveCount(0);

  const filter = page.getByRole("combobox", { name: "Candidate status" });
  await filter.click();
  await page.getByRole("option", { name: "Reviewed" }).click();
  await expect(
    page.getByRole("heading", { name: "1 candidates" }),
  ).toBeVisible();
});


test("shows recent discovery run history", async ({ page }) => {
  await page.goto("/release-inbox");

  const runs = page.getByRole("region", { name: "Run history" });
  await expect(runs.getByText("Candidate Inbox Anime", { exact: true })).toBeVisible();
  await expect(runs.getByText("completed", { exact: true })).toBeVisible();
  await expect(runs.getByText("1 candidates", { exact: true })).toBeVisible();
});
