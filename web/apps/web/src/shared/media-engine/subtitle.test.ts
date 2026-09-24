import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  ready: Promise.resolve(),
  destroy: vi.fn(),
}));

vi.mock("jassub", () => ({
  default: class JASSUB {
    ready = mocks.ready;
    destroy = mocks.destroy;
  },
}));

import { JassubSubtitleEngine } from "./subtitle";

describe("JassubSubtitleEngine", () => {
  it("loads ASS subtitles with playback fonts", async () => {
    const video = {} as HTMLVideoElement;
    const engine = new JassubSubtitleEngine();
    const subtitle = {
      id: "subtitle-id",
      language: "ko",
      title: "Korean",
      is_default: true,
      is_forced: false,
      format: "ass",
      url: "https://media.example.test/subtitle.ass",
    };
    const fonts = [
      {
        id: "font-id",
        name: "Noto Sans",
        mime_type: "font/ttf",
        url: "https://media.example.test/font.ttf",
      },
    ];

    await engine.attach(video, subtitle, fonts);

    await expect(mocks.ready).resolves.toBeUndefined();
  });

  it("destroys the renderer on detach", async () => {
    const engine = new JassubSubtitleEngine();

    await engine.attach(
      {} as HTMLVideoElement,
      {
        id: "subtitle-id",
        language: "ko",
        title: "Korean",
        is_default: true,
        is_forced: false,
        format: "ass",
        url: "https://media.example.test/subtitle.ass",
      },
      [],
    );
    engine.detach();

    expect(mocks.destroy).toHaveBeenCalledTimes(1);
  });
});
