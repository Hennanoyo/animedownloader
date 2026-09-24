import { expect, test } from "@playwright/test";

const episodeId = process.env.REAL_PLAYBACK_EPISODE_ID;

test.describe("real playback smoke", () => {
  test.skip(!episodeId, "REAL_PLAYBACK_EPISODE_ID is required.");

  test("loads and exercises a real Episode playback", async ({ page }) => {
    const playbackResponse = page.waitForResponse(
      (response) =>
        response.url().includes(
          `/api/episodes/${episodeId}/playback`,
        ) && response.ok(),
    );

    await page.goto(`/episodes/${episodeId}`);
    const playback = await (await playbackResponse).json();

    const player = page.getByRole("region", { name: "Video player" });
    const video = page.getByTestId("video-player");

    await expect(player).toBeVisible();
    await expect(video).toBeVisible();

    await expect
      .poll(() => video.evaluate((element) => (element as HTMLVideoElement).readyState))
      .toBeGreaterThanOrEqual(2);

    const initialTime = await video.evaluate((element) => (element as HTMLVideoElement).currentTime);

    await page.getByRole("button", { name: "Play" }).click();

    await expect
      .poll(() => video.evaluate((element) => (element as HTMLVideoElement).currentTime), {
        timeout: 15_000,
      })
      .toBeGreaterThan(initialTime);

    const subtitleSelector = page.locator("select").first();
    if (playback.subtitles.length > 0) {
      await expect(subtitleSelector).toBeVisible();
      const subtitleOptions = await subtitleSelector.locator("option").count();
      expect(subtitleOptions).toBeGreaterThan(1);

      await subtitleSelector.selectOption({ index: 1 });
      await expect
        .poll(() => page.locator(".JASSUB").count(), {
          timeout: 15_000,
        })
        .toBeGreaterThan(0);
    }

    const timeline = page.getByTestId("timeline-track");
    if (playback.thumbnails !== null) {
      await timeline.hover({ position: { x: 250, y: 2 } });
      await expect(
        page.getByRole("img", { name: /Preview at/ }),
      ).toBeVisible();
    }

    await page.getByRole("button", { name: "Enter fullscreen" }).click();
    await expect(
      page.getByRole("button", { name: "Exit fullscreen" }),
    ).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(
      page.getByRole("button", { name: "Enter fullscreen" }),
    ).toBeVisible();
  });
});
