import { expect, test } from "@playwright/test";
import type { AnimePipeline } from "../apps/web/src/entities/anime/model/pipeline";

const ANIME_ID = "019a0000-0000-7000-8000-000000000010";
let pipelineRequests = 0;
let pipelineResponse: AnimePipeline;
const EPISODE_ID = "019a0000-0000-7000-8000-000000000011";
const THUMBNAIL_URL = "https://e2e.invalid/anime/episode-one-sprite.jpg";

const anime = {"id":"019a0000-0000-7000-8000-000000000010","title":"Browser Smoke Anime","titles":{"romaji":"Browser Smoke Romaji","jp":"ブラウザスモークアニメ","en":"Browser Smoke English"},"year":2026,"season":"fall","weekday":"friday","air_time":"23:00:00","timezone":"Asia/Tokyo","created_at":"2026-09-25T00:00:00Z","updated_at":"2026-09-25T00:00:00Z","episodes":[{"id":"019a0000-0000-7000-8000-000000000011","anime_id":"019a0000-0000-7000-8000-000000000010","episode_number":1,"title":"Episode One","source":"nyaa","source_id":"e2e-1","source_title":"Episode One","source_url":"https://e2e.invalid/release/1","torrent_url":"https://e2e.invalid/download/1.torrent","size":"1 GiB","seeders":8,"leechers":1,"downloads":10,"info_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","download_status":"completed","conversion_status":"completed","created_at":"2026-09-25T00:00:00Z","updated_at":"2026-09-25T00:00:00Z"}]};
const pipeline: AnimePipeline = {"anime_id":"019a0000-0000-7000-8000-000000000010","episodes":[{"episode_id":"019a0000-0000-7000-8000-000000000011","episode_number":1,"title":"Episode One","download":{"job_id":"019a0000-0000-7000-8000-000000000099","status":"completed","downloaded_bytes":1048576,"total_bytes":1048576,"error_message":null,"updated_at":"2026-09-25T00:05:00Z"},"processing":{"job_id":"019a0000-0000-7000-8000-000000000100","preparation_job_id":"019a0000-0000-7000-8000-000000000101","status":"completed","progress_percent":100,"playable_ready":true,"error_message":null},"subtitles":"completed","attachments":"completed","streaming":{"job_id":"019a0000-0000-7000-8000-000000000102","status":"completed","progress_percent":100,"hls_ready":true,"dash_ready":true,"error_message":null},"thumbnail":{"status":"completed","progress_percent":100,"url":"https://e2e.invalid/anime/episode-one-sprite.jpg","vtt_url":"https://e2e.invalid/anime/episode-one-sprite.vtt","error_message":null},"current_stage":null,"playback_ready":true,"active":false}]};

const transparentPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

test.beforeEach(async ({ page }) => {
  pipelineResponse = structuredClone(pipeline);
  await page.route(`**/api/animes/${ANIME_ID}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(anime),
    });
  });
  pipelineRequests = 0;
  await page.route(`**/api/animes/${ANIME_ID}/pipeline`, async (route) => {
    pipelineRequests += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(pipelineResponse),
    });
  });
  await page.route(
    "**/api/releases/discover?**",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          query: "ExampleSubs Browser Smoke Anime 1",
          warnings: [],
          search_profile_version: null,
          items: [
            {
              release: {
                source: "nyaa",
                id: "e2e-release-1",
                title: "[ExampleSubs] Browser Smoke Anime - 01 [1080p][HEVC]",
                page_url: "https://e2e.invalid/release/1",
                torrent_url: "https://e2e.invalid/download/1.torrent",
                published_at: "2026-09-25T00:00:00Z",
                size: "1 GiB",
                seeders: 15,
                leechers: 1,
                downloads: 20,
                info_hash: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
              },
              parsed: {
                provider_source: "nyaa",
                source_id: "e2e-release-1",
                original_title: "[ExampleSubs] Browser Smoke Anime - 01 [1080p][HEVC]",
                normalized_title: "[ExampleSubs] Browser Smoke Anime - 01 [1080p][HEVC]",
                release_group: "ExampleSubs",
                series_title: "Browser Smoke Anime",
                episode_number: 1,
                episode_title: null,
                season_number: null,
                resolution: "1080p",
                source: "WEB",
                video_codec: "HEVC",
                audio_codec: null,
                bit_depth: 10,
                status: "parsed",
                warnings: [],
                failed_required_fields: [],
                parser_profile_version: null,
              },
            },
          ],
        }),
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

  const thumbnail = page.getByRole("link", {
    name: "Episode One thumbnail",
  });
  await expect(thumbnail).toBeVisible();
  await expect(thumbnail).toHaveAttribute("href", `/episodes/${EPISODE_ID}`);

  await expect(
    thumbnail.locator("div").first(),
  ).toHaveCSS("background-size", "1500% 1200%");

  const showDetails = page.getByRole("button", { name: "Show details" });
  await expect(showDetails).toBeVisible();
  await showDetails.click();

  const pipelineStatus = page.getByLabel("Media pipeline status");
  await expect(pipelineStatus.getByText("Download", { exact: true })).toBeVisible();
  await expect(pipelineStatus.getByText("Processing", { exact: true })).toBeVisible();
  await expect(pipelineStatus.getByText("Preview", { exact: true })).toBeVisible();
  await expect(pipelineStatus.getByText("Streaming", { exact: true })).toBeVisible();
  await expect(
    pipelineStatus.locator('[data-completed="true"]'),
  ).toHaveCount(4);
  await expect(pipelineStatus.getByText("Playable media ready")).toBeVisible();
  await expect(pipelineStatus.getByText("Subtitles")).toBeVisible();
  await expect(pipelineStatus.getByText("Attachments")).toBeVisible();
  await expect(pipelineStatus.getByText("HLS ready")).toBeVisible();
  await expect(pipelineStatus.getByText("DASH ready")).toBeVisible();

  await expect(
    page.getByRole("link", { name: "Episode One", exact: true }),
  ).toHaveAttribute("href", `/episodes/${EPISODE_ID}`);
  await expect(
    page.getByRole("button", { name: "Episode actions" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Episode actions" }).click();
  await expect(
    page.getByRole("menuitem", { name: "Download again" }),
  ).toBeVisible();
  await expect(
    page.getByRole("menuitem", { name: "Delete download record" }),
  ).toBeVisible();
  await expect(
    page.getByRole("menuitem", { name: "Delete episode" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "Hide details" }).click();
  await expect(pipelineStatus).toBeHidden();
});


test("receives live pipeline updates without polling", async ({ page }) => {
  await page.addInitScript(() => {
    class MockWebSocket {
      static instances: MockWebSocket[] = [];
      readonly url: string;
      readyState = 0;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onclose: ((event: Event) => void) | null = null;

      constructor(url: string) {
        this.url = url;
        MockWebSocket.instances.push(this);
        setTimeout(() => {
          this.readyState = 1;
          this.onopen?.(new Event("open"));
          this.onmessage?.(
            new MessageEvent("message", {
              data: JSON.stringify({
                version: 1,
                type: "job.ready",
                job_type: "all",
                emitted_at: "2026-09-25T00:00:00Z",
              }),
            }),
          );
        }, 0);
      }

      close() {
        if (this.readyState === 3) {
          return;
        }
        this.readyState = 3;
        this.onclose?.(new Event("close"));
      }

      emit(payload: unknown) {
        this.onmessage?.(
          new MessageEvent("message", {
            data: JSON.stringify(payload),
          }),
        );
      }
    }

    Object.defineProperty(globalThis, "WebSocket", {
      configurable: true,
      value: MockWebSocket,
    });
    Object.defineProperty(window, "__emitPipelineEvent", {
      configurable: true,
      value: (payload: unknown) => {
        MockWebSocket.instances.at(-1)?.emit(payload);
      },
    });
  });

  const activePipeline = structuredClone(pipeline);
  activePipeline.episodes[0].download = {
    ...activePipeline.episodes[0].download,
    job_id: "019a0000-0000-7000-8000-000000000099",
    status: "downloading",
    downloaded_bytes: 524288,
    total_bytes: 1048576,
    error_message: null,
    updated_at: "2026-09-25T00:05:00Z",
  };
  activePipeline.episodes[0].processing.status = "pending";
  activePipeline.episodes[0].processing.progress_percent = 0;
  activePipeline.episodes[0].playback_ready = false;
  activePipeline.episodes[0].thumbnail.status = "pending";
  activePipeline.episodes[0].thumbnail.progress_percent = 0;
  activePipeline.episodes[0].thumbnail.url = null;
  activePipeline.episodes[0].thumbnail.vtt_url = null;
  activePipeline.episodes[0].streaming.status = "pending";
  activePipeline.episodes[0].streaming.hls_ready = false;
  activePipeline.episodes[0].streaming.dash_ready = false;
  activePipeline.episodes[0].current_stage = "download";
  activePipeline.episodes[0].active = true;

  pipelineResponse = activePipeline;

  await page.goto(`/animes/${ANIME_ID}`);
  const showDetails = page.getByRole("button", { name: "Show details" });
  const pipelineDetailsToggle = page.getByRole("button", {
    name: /^(Show|Hide) details$/,
  });
  await expect(pipelineDetailsToggle).toBeVisible();
  if (await showDetails.isVisible()) {
    await showDetails.click();
  }
  await expect(page.locator('[aria-label="Download progress"]')).toBeVisible();

  const pipelineStatus = page.getByLabel("Media pipeline status");

  await page.waitForTimeout(1000);
  const requestsAfterRealtimeConnect = pipelineRequests;

  const emitPipelineEvent = (payload: unknown) =>
    page.evaluate((eventPayload) => {
      const windowWithEmitter = window as unknown as {
        __emitPipelineEvent: (payload: unknown) => void;
      };
      windowWithEmitter.__emitPipelineEvent(eventPayload);
    }, payload);

  await emitPipelineEvent({
    version: 1,
    type: "job.progress",
    job_type: "download",
    job_id: "019a0000-0000-7000-8000-000000000099",
    status: "downloading",
    progress_percent: 100,
    downloaded_bytes: 1048576,
    total_bytes: 1048576,
    error_message: null,
    stage: null,
    emitted_at: "2026-09-25T00:06:00Z",
  });

  await expect(page.getByText("1.0 MiB / 1.0 MiB", { exact: true })).toBeVisible();

  await emitPipelineEvent({
    version: 1,
    type: "job.progress",
    job_type: "media-preparation",
    job_id: "019a0000-0000-7000-8000-000000000101",
    status: "processing",
    progress_percent: 0,
    downloaded_bytes: null,
    total_bytes: null,
    error_message: null,
    stage: "processing",
    emitted_at: "2026-09-25T00:06:00.500Z",
  });
  await expect(
    page.getByRole("progressbar", { name: "Preparing" }),
  ).toBeVisible();

  await emitPipelineEvent({
    version: 1,
    type: "job.progress",
    job_type: "media-preparation",
    job_id: "019a0000-0000-7000-8000-000000000101",
    status: "processing",
    progress_percent: 42,
    downloaded_bytes: null,
    total_bytes: null,
    error_message: null,
    stage: "processing",
    emitted_at: "2026-09-25T00:06:01Z",
  });
  await expect(
    page.getByRole("progressbar", { name: "Preparation" }),
  ).toHaveAttribute("aria-valuenow", "42");

  await emitPipelineEvent({
    version: 1,
    type: "job.progress",
    job_type: "media-preparation",
    job_id: "019a0000-0000-7000-8000-000000000101",
    status: "processing",
    progress_percent: 68,
    downloaded_bytes: null,
    total_bytes: null,
    error_message: null,
    stage: "preview",
    emitted_at: "2026-09-25T00:06:02Z",
  });
  await expect(
    page.getByRole("progressbar", { name: "Sprite" }),
  ).toHaveAttribute("aria-valuenow", "68");

  await expect(
    pipelineStatus.locator('span[data-current="true"]'),
  ).toHaveCount(1);
  await expect(
    pipelineStatus.locator(
      'span[data-current="false"][data-status="processing"]',
    ),
  ).toHaveCount(2);

  await emitPipelineEvent({
    version: 1,
    type: "job.progress",
    job_type: "media-packaging",
    job_id: "019a0000-0000-7000-8000-000000000102",
    status: "processing",
    progress_percent: 73,
    downloaded_bytes: null,
    total_bytes: null,
    error_message: null,
    stage: "streaming",
    emitted_at: "2026-09-25T00:06:03Z",
  });
  await expect(
    page.getByRole("progressbar", { name: "Packaging" }),
  ).toHaveAttribute("aria-valuenow", "73");

  await page.waitForTimeout(2500);
  expect(pipelineRequests).toBe(requestsAfterRealtimeConnect);
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
    job_id: "019a0000-0000-7000-8000-000000000102",
    status: "pending",
    progress_percent: 0,
    hls_ready: false,
    dash_ready: false,
    error_message: null,
  };
  pendingPipeline.episodes[0].current_stage = "streaming";
  pendingPipeline.episodes[0].active = true;

  pipelineResponse = pendingPipeline;

  await page.goto(`/animes/${ANIME_ID}`);
  const continueButton = page.getByRole("button", { name: "Continue" });
  await expect(continueButton).not.toBeVisible();
  await expect(continueButton).toBeVisible();
  await continueButton.click();
  await expect.poll(() => retryRequests).toBe(1);
  await expect(
    page.getByRole("button", { name: "Episode actions" }),
  ).toBeVisible();

});

test("keeps live download controls inside the download stage", async ({ page }) => {
  const activePipeline = structuredClone(pipeline);
  activePipeline.episodes[0].download = {
    ...activePipeline.episodes[0].download,
    job_id: "019a0000-0000-7000-8000-000000000099",
    status: "downloading",
    downloaded_bytes: 524288,
    total_bytes: 1048576,
    error_message: null,
    updated_at: "2026-09-25T00:05:00Z",
  };
  activePipeline.episodes[0].processing.status = "pending";
  activePipeline.episodes[0].processing.progress_percent = 0;
  activePipeline.episodes[0].playback_ready = false;
  activePipeline.episodes[0].thumbnail.status = "pending";
  activePipeline.episodes[0].thumbnail.progress_percent = 0;
  activePipeline.episodes[0].thumbnail.url = null;
  activePipeline.episodes[0].thumbnail.vtt_url = null;
  activePipeline.episodes[0].streaming.status = "pending";
  activePipeline.episodes[0].streaming.hls_ready = false;
  activePipeline.episodes[0].streaming.dash_ready = false;
  activePipeline.episodes[0].current_stage = "download";
  activePipeline.episodes[0].active = true;

  pipelineResponse = activePipeline;

  await page.goto(`/animes/${ANIME_ID}`);
  const showDetails = page.getByRole("button", { name: "Show details" });
  const pipelineDetailsToggle = page.getByRole("button", {
    name: /^(Show|Hide) details$/,
  });
  await expect(pipelineDetailsToggle).toBeVisible();
  if (await showDetails.isVisible()) {
    await showDetails.click();
  }
  await expect(page.locator('[aria-label="Download progress"]')).toBeVisible();
  await expect(
    page.locator('[aria-label="Download progress"]').getByText("Downloading", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Pause download" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Cancel download" }),
  ).toBeVisible();

});


test("discovers parsed releases from the anime detail page", async ({ page }) => {
  await page.goto("/animes/" + ANIME_ID);

  const discovery = page.getByRole("region", { name: "Find releases" });
  await expect(
    discovery.getByRole("heading", { name: "Find releases" }),
  ).toBeVisible();

  const titleInput = discovery.getByRole("combobox", {
    name: "Title",
    exact: true,
  });
  await expect(titleInput).toHaveValue("Browser Smoke Romaji");

  const titleSourceButton = discovery.getByRole("button", {
    name: "Romaji",
    exact: true,
  });
  await titleSourceButton.click();
  await expect(
    page.getByRole("option", { name: "English", exact: true }),
  ).toBeVisible();
  await page.getByRole("option", { name: "English", exact: true }).click();
  await expect(titleInput).toHaveValue("Browser Smoke English");

  await titleInput.fill("Browser Smoke Custom");

  const rows = discovery.locator("[data-search-field]");
  const groupCheckbox = discovery.getByRole("checkbox", {
    name: "Enable Group",
  });
  const groupCheckboxToggle = discovery.locator(
    '[data-search-field-toggle="group"]',
  );
  const rowBeforeToggle = await rows.nth(0).boundingBox();
  await groupCheckboxToggle.click();
  await expect(groupCheckbox).not.toBeChecked();
  const rowAfterDisable = await rows.nth(0).boundingBox();
  await groupCheckboxToggle.click();
  await expect(groupCheckbox).toBeChecked();
  const rowAfterEnable = await rows.nth(0).boundingBox();

  expect(rowBeforeToggle?.y).toBe(rowAfterDisable?.y);
  expect(rowBeforeToggle?.height).toBe(rowAfterDisable?.height);
  expect(rowBeforeToggle?.y).toBe(rowAfterEnable?.y);
  expect(rowBeforeToggle?.height).toBe(rowAfterEnable?.height);
  await expect(rows.nth(0)).toHaveAttribute("data-search-field", "group");
  await expect(rows.nth(1)).toHaveAttribute("data-search-field", "title");

  const titleHandle = discovery.getByRole("button", {
    name: "Reorder Title",
  });
  await expect(titleHandle).toHaveAttribute("draggable", "true");
  await titleHandle.press("Space");
  await titleHandle.press("ArrowDown");
  await titleHandle.press("Space");
  await expect(rows.nth(1)).toHaveAttribute("data-search-field", "episode");
  await expect(rows.nth(2)).toHaveAttribute("data-search-field", "title");

  await discovery
    .getByRole("combobox", { name: "Episode", exact: true })
    .fill("1");
  const episodeInput = discovery.getByRole("combobox", {
    name: "Episode",
    exact: true,
  });
  await episodeInput.press("Escape");

  await discovery
    .getByRole("combobox", { name: "Resolution", exact: true })
    .fill("1080p");
  const resolutionInput = discovery.getByRole("combobox", {
    name: "Resolution",
    exact: true,
  });
  await resolutionInput.press("Escape");

  const codecInput = discovery.getByRole("combobox", {
    name: "Codec",
    exact: true,
  });
  await codecInput.fill("HEVC");
  await codecInput.press("Escape");
  await discovery
    .getByRole("button", { name: "Discover releases" })
    .click();

  await expect(
    discovery.locator("strong").filter({ hasText: "1 candidates" }),
  ).toBeVisible();
  const resultCard = discovery.locator("article").filter({
    hasText: "[ExampleSubs] Browser Smoke Anime - 01 [1080p][HEVC]",
  });
  await expect(
    resultCard.getByRole("heading", {
      name: "[ExampleSubs] Browser Smoke Anime - 01 [1080p][HEVC]",
    }),
  ).toBeVisible();
  await expect(resultCard).toContainText("parsed");
  await expect(resultCard).toContainText("Browser Smoke Anime");
  await expect(resultCard).toContainText("1080p");
  await expect(resultCard).toContainText("HEVC");
});
