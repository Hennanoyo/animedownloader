import { expect, test } from "@playwright/test";
import type { AnimePipeline } from "../apps/web/src/entities/anime/model/pipeline";

const ANIME_ID = "019a0000-0000-7000-8000-000000000010";
const EPISODE_ID = "019a0000-0000-7000-8000-000000000011";
const THUMBNAIL_URL = "https://e2e.invalid/anime/episode-one-sprite.jpg";

const anime = {"id":"019a0000-0000-7000-8000-000000000010","title":"Browser Smoke Anime","year":2026,"season":"fall","weekday":"friday","air_time":"23:00:00","timezone":"Asia/Tokyo","created_at":"2026-09-25T00:00:00Z","updated_at":"2026-09-25T00:00:00Z","episodes":[{"id":"019a0000-0000-7000-8000-000000000011","anime_id":"019a0000-0000-7000-8000-000000000010","episode_number":1,"title":"Episode One","source":"nyaa","source_id":"e2e-1","source_title":"Episode One","source_url":"https://e2e.invalid/release/1","torrent_url":"https://e2e.invalid/download/1.torrent","size":"1 GiB","seeders":8,"leechers":1,"downloads":10,"info_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","download_status":"completed","conversion_status":"completed","created_at":"2026-09-25T00:00:00Z","updated_at":"2026-09-25T00:00:00Z"}]};
const pipeline: AnimePipeline = {"anime_id":"019a0000-0000-7000-8000-000000000010","episodes":[{"episode_id":"019a0000-0000-7000-8000-000000000011","episode_number":1,"title":"Episode One","download":{"status":"completed","downloaded_bytes":1048576,"total_bytes":1048576,"error_message":null},"processing":{"status":"completed","progress_percent":100,"playable_ready":true,"error_message":null},"subtitles":"completed","attachments":"completed","streaming":{"status":"completed","hls_ready":true,"dash_ready":true,"error_message":null},"thumbnail":{"status":"completed","progress_percent":100,"url":"https://e2e.invalid/anime/episode-one-sprite.jpg","vtt_url":"https://e2e.invalid/anime/episode-one-sprite.vtt","error_message":null},"current_stage":null,"playback_ready":true,"active":false}]};

const transparentPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

test.beforeEach(async ({ page }) => {
  await page.route(`**/api/animes/${ANIME_ID}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(anime),
    });
  });
  await page.route(`**/api/animes/${ANIME_ID}/pipeline`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(pipeline),
    });
  });
  await page.route(
    `**/api/episodes/${EPISODE_ID}/download-jobs/latest`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "null",
      });
    },
  );
  await page.route(THUMBNAIL_URL, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "image/png",
      body: transparentPng,
    });
  });
});

test("renders episode media pipeline and sprite thumbnail", async ({ page }, testInfo) => {
  await page.goto(`/animes/${ANIME_ID}`);

  await expect(
    page.getByRole("heading", { name: "Browser Smoke Anime" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Episodes" }),
  ).toBeVisible();
  await expect(page.getByText("Episode One")).toBeVisible();

  const thumbnail = page.getByRole("img", {
    name: "Episode One thumbnail",
  });
  await expect(thumbnail).toBeVisible();
  await expect(thumbnail).toHaveCSS("background-size", "1500% 1200%");

  const pipelineStatus = page.getByLabel("Media pipeline status");
  await expect(pipelineStatus.getByText("Download", { exact: true })).toBeVisible();
  await expect(pipelineStatus.getByText("Processing", { exact: true })).toBeVisible();
  await expect(pipelineStatus.getByText("Preview", { exact: true })).toBeVisible();
  await expect(pipelineStatus.getByText("Streaming", { exact: true })).toBeVisible();
  await expect(
    pipelineStatus.getByText("Completed", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByText("HLS ready · DASH ready")).toBeVisible();
  await expect(
    pipelineStatus.getByRole("progressbar", { name: "Preparation" }),
  ).toHaveAttribute("aria-valuenow", "100");
  await expect(
    pipelineStatus.getByRole("progressbar", { name: "Sprite" }),
  ).toHaveAttribute("aria-valuenow", "100");

  await expect(
    page.getByRole("link", { name: "Play" }),
  ).toHaveAttribute("href", `/episodes/${EPISODE_ID}`);
  await expect(
    page.getByRole("button", { name: "Download" }),
  ).toBeVisible();
});


test("offers pipeline continuation without restarting a completed download", async ({ page }) => {
  let retryRequests = 0;
  await page.route(
    `**/api/episodes/${EPISODE_ID}/pipeline/retry`,
    async (route) => {
      retryRequests += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          stage: "streaming",
          job_id: "019a0000-0000-7000-8000-000000000099",
          status: "pending",
        }),
      });
    },
  );

  const pendingPipeline = structuredClone(pipeline);
  pendingPipeline.episodes[0].streaming = {
    status: "pending",
    hls_ready: false,
    dash_ready: false,
    error_message: null,
  };
  pendingPipeline.episodes[0].current_stage = "streaming";
  pendingPipeline.episodes[0].active = true;

  await page.unroute(`**/api/animes/${ANIME_ID}/pipeline`);
  await page.route(`**/api/animes/${ANIME_ID}/pipeline`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(pendingPipeline),
    });
  });

  await page.goto(`/animes/${ANIME_ID}`);
  const continueButton = page.getByRole("button", { name: "Continue streaming" });
  await expect(continueButton).toBeVisible();
  await continueButton.click();
  await expect.poll(() => retryRequests).toBe(1);
  await expect(page.getByRole("button", { name: "Download" })).toBeVisible();
});

test("moves live download details into the full-width download panel", async ({ page }, testInfo) => {
  const activePipeline = structuredClone(pipeline);
  activePipeline.episodes[0].download = {
    status: "downloading",
    downloaded_bytes: 524288,
    total_bytes: 1048576,
    error_message: null,
  };
  activePipeline.episodes[0].processing.status = "pending";
  activePipeline.episodes[0].processing.progress_percent = 0;
  activePipeline.episodes[0].playback_ready = false;
  activePipeline.episodes[0].current_stage = "download";
  activePipeline.episodes[0].active = true;

  await page.unroute(`**/api/animes/${ANIME_ID}/pipeline`);
  await page.route(`**/api/animes/${ANIME_ID}/pipeline`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(activePipeline),
    });
  });
  await page.unroute(
    `**/api/episodes/${EPISODE_ID}/download-jobs/latest`,
  );
  await page.route(
    `**/api/episodes/${EPISODE_ID}/download-jobs/latest`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "019a0000-0000-7000-8000-000000000098",
          episode_id: EPISODE_ID,
          status: "downloading",
          downloaded_bytes: 524288,
          total_bytes: 1048576,
          attempt_count: 1,
          error_message: null,
          started_at: "2026-09-25T00:00:00Z",
          completed_at: null,
          created_at: "2026-09-25T00:00:00Z",
          updated_at: "2026-09-25T00:00:00Z",
        }),
      });
    },
  );

  await page.goto(`/animes/${ANIME_ID}`);
  await expect(page.getByLabel("Download progress")).toBeVisible();
  await expect(
    page.getByLabel("Download progress").getByText("Downloading", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Pause" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
});
