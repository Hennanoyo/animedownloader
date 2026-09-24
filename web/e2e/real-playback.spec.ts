import { expect, test } from "@playwright/test";

const episodeId = process.env.REAL_PLAYBACK_EPISODE_ID;

test.describe("real playback smoke", () => {
  test.skip(!episodeId, "REAL_PLAYBACK_EPISODE_ID is required.");

  test("loads and exercises a real Episode playback", async ({ page }) => {
    await page.goto(`/episodes/${episodeId}`);

    const player = page.getByRole("region", { name: "Video player" });
    const video = page.getByTestId("video-player");

    await expect(player).toBeVisible();
    await expect(video).toBeVisible();

    await expect
      .poll(() => video.evaluate((element) => element.readyState))
      .toBeGreaterThanOrEqual(2);

    const initialTime = await video.evaluate((element) => element.currentTime);

    await page.getByRole("button", { name: "Play" }).click();

    await expect
      .poll(() => video.evaluate((element) => element.currentTime), {
        timeout: 15_000,
      })
      .toBeGreaterThan(initialTime);

    const subtitleSelector = page.locator("select").first();
    if (await subtitleSelector.count()) {
      await expect(subtitleSelector).toBeVisible();

      const subtitleOptions = await subtitleSelector.locator("option").count();
      if (subtitleOptions > 1) {
        await subtitleSelector.selectOption({ index: 1 });
        await expect(page.locator(".JASSUB")).toHaveCount(1);
      }
    }

    const timeline = page.getByTestId("timeline-track");
    await timeline.hover({ position: { x: 250, y: 2 } });

    if (await page.getByRole("img", { name: /Preview at/ }).count()) {
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
