import { expect, test } from "@playwright/test";

const EPISODE_ID = "019a0000-0000-7000-8000-000000000001";
const SPRITE_URL = "https://e2e.invalid/player/preview.png";
const THUMBNAIL_VTT_URL = "https://e2e.invalid/player/thumbnails.vtt";

const playback = {
  anime_id: "019a0000-0000-7000-8000-000000000002",
  episode_id: EPISODE_ID,
  episode_number: 1,
  title: "Browser Smoke Episode",
  duration_seconds: 120,
  video: {
    direct: {
      url: "https://e2e.invalid/player/video.mp4",
      mime_type: "video/mp4",
    },
    hls: null,
    dash: null,
  },
  subtitles: [],
  fonts: [],
  chapters: [
    {
      id: "019a0000-0000-7000-8000-000000000003",
      title: "Opening",
      start_time_seconds: 12,
      end_time_seconds: 30,
    },
  ],
  thumbnails: {
    sprite_url: SPRITE_URL,
    vtt_url: THUMBNAIL_VTT_URL,
  },
};

const thumbnailVtt = `WEBVTT

00:00:00.000 --> 00:00:10.000
${SPRITE_URL}#xywh=0,0,160,90

00:00:10.000 --> 00:00:20.000
${SPRITE_URL}#xywh=160,0,160,90
`;

const transparentPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const currentTimes = new WeakMap<HTMLMediaElement, number>();
    const pausedState = new WeakMap<HTMLMediaElement, boolean>();

    Object.defineProperty(HTMLMediaElement.prototype, "currentTime", {
      configurable: true,
      get() {
        return currentTimes.get(this) ?? 0;
      },
      set(value: number) {
        currentTimes.set(this, value);
        this.dispatchEvent(new Event("timeupdate"));
      },
    });

    Object.defineProperty(HTMLMediaElement.prototype, "duration", {
      configurable: true,
      get() {
        return 120;
      },
    });

    Object.defineProperty(HTMLMediaElement.prototype, "paused", {
      configurable: true,
      get() {
        return pausedState.get(this) ?? true;
      },
    });

    HTMLMediaElement.prototype.canPlayType = () => "probably";

    HTMLMediaElement.prototype.load = function () {
      pausedState.set(this, true);
      queueMicrotask(() => {
        this.dispatchEvent(new Event("loadedmetadata"));
        this.dispatchEvent(new Event("durationchange"));
        this.dispatchEvent(new Event("canplay"));
      });
    };

    HTMLMediaElement.prototype.play = function () {
      pausedState.set(this, false);
      this.dispatchEvent(new Event("play"));
      return Promise.resolve();
    };

    HTMLMediaElement.prototype.pause = function () {
      pausedState.set(this, true);
      this.dispatchEvent(new Event("pause"));
    };

    let fullscreenElement: Element | null = null;
    Object.defineProperty(document, "fullscreenElement", {
      configurable: true,
      get: () => fullscreenElement,
    });

    Element.prototype.requestFullscreen = async function () {
      fullscreenElement = this;
      document.dispatchEvent(new Event("fullscreenchange"));
    };

    document.exitFullscreen = async function () {
      fullscreenElement = null;
      document.dispatchEvent(new Event("fullscreenchange"));
    };
  });

  await page.route(
    `**/api/episodes/${EPISODE_ID}/playback`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(playback),
      });
    },
  );

  await page.route(THUMBNAIL_VTT_URL, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/vtt",
      body: thumbnailVtt,
    });
  });

  await page.route(SPRITE_URL, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "image/png",
      body: transparentPng,
    });
  });
});

test("covers playback controls, keyboard priority, thumbnails, and fullscreen", async ({
  page,
}) => {
  await page.goto(`/episodes/${EPISODE_ID}`);

  const player = page.getByRole("region", { name: "Video player" });
  const video = page.getByTestId("video-player");

  await expect(player).toBeFocused();

  await page.keyboard.press("Space");
  await expect(
    page.getByRole("button", { name: "Pause" }),
  ).toBeVisible();

  await page.keyboard.press("ArrowRight");
  await expect
    .poll(() => video.evaluate((element) => element.currentTime))
    .toBe(5);

  await page.keyboard.press("ArrowDown");
  await expect
    .poll(() => video.evaluate((element) => element.volume))
    .toBeCloseTo(0.95);

  await page.keyboard.press("m");
  await expect
    .poll(() => video.evaluate((element) => element.muted))
    .toBe(true);

  await player.focus();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("slider", { name: "Seek" })).toBeFocused();

  await page.keyboard.press("Tab");
  const playButton = page.getByRole("button", { name: "Pause" });
  await expect(playButton).toBeFocused();

  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Play" })).toBeFocused();

  await page.evaluate(() => {
    document.body.insertAdjacentHTML(
      "beforeend",
      '<input id="browser-smoke-input" aria-label="Browser smoke input" />',
    );
  });

  const input = page.getByRole("textbox", { name: "Browser smoke input" });
  await input.focus();
  await page.keyboard.press("m");
  await expect(input).toHaveValue("m");
  await expect
    .poll(() => video.evaluate((element) => element.muted))
    .toBe(true);

  await page.evaluate(() => {
    document.body.style.minHeight = "200vh";
    const surface = document.createElement("div");
    surface.id = "browser-smoke-surface";
    surface.tabIndex = 0;
    surface.style.position = "fixed";
    surface.style.top = "0";
    surface.style.left = "0";
    surface.style.width = "1px";
    surface.style.height = "1px";
    document.body.append(surface);
    surface.focus();
    window.scrollTo(0, 0);
  });

  await page.keyboard.press("ArrowDown");
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);

  await page.getByTestId("timeline-track").hover({ position: { x: 250, y: 2 } });
  await expect(
    page.getByRole("img", { name: /Preview at/ }),
  ).toBeVisible();

  const fullscreenButton = page.getByRole("button", {
    name: "Enter fullscreen",
  });
  await fullscreenButton.click();
  await expect(
    page.getByRole("button", { name: "Exit fullscreen" }),
  ).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Enter fullscreen" }),
  ).toBeVisible();
});
