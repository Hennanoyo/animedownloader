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

let candidateStatus: "new" | "reviewed" | "accepted" | "rejected" | "stale" = "new";

const existingEpisode = {
  id: "019a0000-0000-7000-8000-000000000030",
  anime_id: ANIME_ID,
  release_group_id: null,
  episode_number: 1,
  title: "Existing Episode",
  source: "nyaa",
  source_id: "old-release",
  source_title: "Old release",
  source_url: "https://e2e.invalid/release/old",
  torrent_url: "https://e2e.invalid/download/old.torrent",
  size: "1 GiB",
  seeders: 4,
  leechers: 1,
  downloads: 10,
  info_hash: "oldhash0123456789oldhash0123456789oldhash01",
  download_status: "not_started",
  conversion_status: "not_started",
  created_at: "2026-09-26T00:00:00Z",
  updated_at: "2026-09-26T00:00:00Z",
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
  automation_status: "idle",
  automation_claimed_at: null,
  automation_completed_at: null,
  automation_error: null,
});

test.beforeEach(async ({ page }) => {
  candidateStatus = "new";

  await page.route("**/api/animes", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([anime]),
    });
  });
  await page.route("**/api/release-discovery/candidates**", async (route) => {
    if (route.request().method() === "POST") {
      const body = JSON.parse(route.request().postData() ?? "{}") as {
        replace_episode_id?: string | null;
      };
      if (body.replace_episode_id) {
        candidateStatus = "accepted";
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "replaced",
            candidate: candidate(),
            episode: {
              ...existingEpisode,
              source_id: "123456",
              source_title: candidate().source_title,
            },
            existing_episode: null,
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "replacement_candidate",
            candidate: candidate(),
            episode: null,
            existing_episode: existingEpisode,
          }),
        });
      }
      return;
    }
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
  await page.route("**/api/episodes/*/download-jobs", async (route) => {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        id: "019a0000-0000-7000-8000-000000000031",
        episode_id: existingEpisode.id,
        status: "pending",
        downloaded_bytes: 0,
        total_bytes: 100,
        attempt_count: 1,
        error_message: null,
        started_at: null,
        completed_at: null,
        created_at: "2026-09-26T00:10:00Z",
        updated_at: "2026-09-26T00:10:00Z",
      }),
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
          queries: [
            {
              id: "019a0000-0000-7000-8000-000000000023",
              position: 1,
              query: "Candidate Inbox Anime",
              status: "completed",
              result_count: 18,
              result_cap_reached: false,
              error_message: null,
              created_at: "2026-09-26T00:00:01Z",
            },
          ],
        },
      ]),
    });
  });
});

test("reviews a persisted discovery candidate in the inbox", async ({ page }) => {
  await page.goto("/release-inbox");

  await expect(
    page.getByRole("heading", { name: "Candidate inbox", exact: true }),
  ).toBeVisible();
  await expect(
    page
      .locator('section[aria-labelledby="candidates-heading"]')
      .getByText("Candidate Inbox Anime", { exact: true }),
  ).toHaveCount(1);
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

  await expect(
    card.getByText("reviewed", { exact: true }),
  ).toBeVisible();
});


test("shows recent discovery run history", async ({ page }) => {
  await page.goto("/release-inbox");

  const runSection = page.locator('section[aria-labelledby="runs-heading"]');
  const runCard = runSection.locator("article").first();
  await expect(runCard).toBeVisible();
  await expect(runCard.getByText("completed", { exact: true })).toBeVisible();
  await expect(
    runCard.getByText("Query diagnostics", { exact: true }),
  ).toBeVisible();
  await expect(
    runCard.getByText("18 results · completed", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "candidates" })).toContainText("1 candidates");
});



test("accepts a candidate and explicitly confirms an episode replacement", async ({ page }) => {
  await page.goto("/release-inbox");

  const card = page.locator("article").filter({
    hasText: "[ExampleSubs] Candidate Inbox Anime - 01 [1080p][HEVC]",
  });

  await card.getByRole("button", { name: "Accept" }).click();

  await expect(card).toContainText(
    'Episode 1 already exists as "Existing Episode".',
  );
  await expect(
    card.getByRole("button", { name: "Replace Episode" }),
  ).toBeVisible();

  await card.getByRole("button", { name: "Replace Episode" }).click();

  await expect(card.getByText("accepted", { exact: true })).toBeVisible();
  await expect(
    card.getByRole("button", { name: "Accept" }),
  ).toHaveCount(0);

  await card.getByRole("button", { name: "Download" }).click();
  await expect(
    card.getByRole("button", { name: "Download" }),
  ).toBeVisible();
  await expect(
    card.getByText("Failed to queue download:", { exact: false }),
  ).toHaveCount(0);
});
