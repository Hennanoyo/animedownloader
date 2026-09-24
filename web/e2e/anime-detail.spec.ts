import { expect, test } from "@playwright/test";

const ANIME_ID = "019a0000-0000-7000-8000-000000000010";
const EPISODE_ID = "019a0000-0000-7000-8000-000000000011";
const THUMBNAIL_URL = "https://e2e.invalid/anime/episode-one-sprite.jpg";

const anime = {"id":"019a0000-0000-7000-8000-000000000010","title":"Browser Smoke Anime","year":2026,"season":"fall","weekday":"friday","air_time":"23:00:00","timezone":"Asia/Tokyo","created_at":"2026-09-25T00:00:00Z","updated_at":"2026-09-25T00:00:00Z","episodes":[{"id":"019a0000-0000-7000-8000-000000000011","anime_id":"019a0000-0000-7000-8000-000000000010","episode_number":1,"title":"Episode One","source":"nyaa","source_id":"e2e-1","source_title":"Episode One","source_url":"https://e2e.invalid/release/1","torrent_url":"https://e2e.invalid/download/1.torrent","size":"1 GiB","seeders":8,"leechers":1,"downloads":10,"info_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","download_status":"completed","conversion_status":"completed","created_at":"2026-09-25T00:00:00Z","updated_at":"2026-09-25T00:00:00Z"}]};
const pipeline = {"anime_id":"019a0000-0000-7000-8000-000000000010","episodes":[{"episode_id":"019a0000-0000-7000-8000-000000000011","episode_number":1,"title":"Episode One","download":{"status":"completed","downloaded_bytes":1048576,"total_bytes":1048576,"error_message":null},"processing":{"status":"completed","playable_ready":true,"error_message":null},"subtitles":"completed","attachments":"completed","streaming":{"status":"completed","hls_ready":true,"dash_ready":true,"error_message":null},"thumbnail":{"status":"completed","url":"https://e2e.invalid/anime/episode-one-sprite.jpg","vtt_url":"https://e2e.invalid/anime/episode-one-sprite.vtt","error_message":null},"playback_ready":true,"active":false}]};

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

test("renders episode media pipeline and sprite thumbnail", async ({ page }) => {
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

  await expect(page.getByText("Download", { exact: true })).toBeVisible();
  await expect(page.getByText("Processing", { exact: true })).toBeVisible();
  await expect(page.getByText("Streaming", { exact: true })).toBeVisible();
  await expect(page.getByText("Preview", { exact: true })).toBeVisible();
  await expect(page.getByText("Completed", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("HLS · DASH")).toBeVisible();

  await expect(
    page.getByRole("link", { name: "Play" }),
  ).toHaveAttribute("href", `/episodes/${EPISODE_ID}`);
  await expect(
    page.getByRole("button", { name: "Download" }),
  ).toBeVisible();
});
