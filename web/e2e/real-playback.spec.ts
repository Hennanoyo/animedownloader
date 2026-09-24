import { expect, test, type Page } from "@playwright/test";
import type { Playback } from "../apps/web/src/features/playback/model/types";

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
    const playback = (await (await playbackResponse).json()) as Playback;

    const player = page.getByRole("region", { name: "Video player" });
    const video = page.getByTestId("video-player");

    await expect(player).toBeVisible();
    await expect(video).toBeVisible();

    const unsupportedHevcCodec = await detectUnsupportedHevc(page, playback);
    if (unsupportedHevcCodec !== null) {
      test.skip(
        true,
        `Browser does not support the real HEVC stream (${unsupportedHevcCodec}); real media playback is skipped.`,
      );
    }

    await expect
      .poll(
        () =>
          video.evaluate(
            (element) => (element as HTMLVideoElement).readyState,
          ),
      )
      .toBeGreaterThanOrEqual(2);

    const initialTime = await video.evaluate(
      (element) => (element as HTMLVideoElement).currentTime,
    );

    await page.getByRole("button", { name: "Play" }).click();

    await expect
      .poll(
        () =>
          video.evaluate(
            (element) => (element as HTMLVideoElement).currentTime,
          ),
        {
          timeout: 15_000,
        },
      )
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

    await player.focus();
    await page.keyboard.press("Escape");
    await expect(
      page.getByRole("button", { name: "Enter fullscreen" }),
    ).toBeVisible();
  });
});

async function detectUnsupportedHevc(
  page: Page,
  playback: Playback,
): Promise<string | null> {
  const hlsUrl = playback.video?.hls?.url;
  if (hlsUrl === null || hlsUrl === undefined) {
    return null;
  }

  return page.evaluate(async (url) => {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `Could not inspect the HLS master playlist (HTTP ${response.status}).`,
      );
    }

    const playlist = await response.text();
    const codecs = Array.from(
      playlist.matchAll(/CODECS="([^"]+)"/g),
      (match) => match[1],
    )
      .filter((value): value is string => value !== undefined)
      .flatMap((value) => value.split(",").map((codec) => codec.trim()));

    const hevcCodec = codecs.find((codec) =>
      /^(hvc1|hev1)(?:\.|$)/i.test(codec),
    );
    if (hevcCodec === undefined) {
      return null;
    }

    const codecString = codecs.join(",");
    const supported =
      typeof MediaSource !== "undefined" &&
      MediaSource.isTypeSupported(
        `video/mp4; codecs="${codecString}"`,
      );

    return supported ? null : hevcCodec;
  }, hlsUrl);
}
