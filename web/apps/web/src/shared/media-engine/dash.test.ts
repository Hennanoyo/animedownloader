import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  reset: vi.fn(),
  initialize: vi.fn(),
  create: vi.fn(),
}));

vi.mock("dashjs", () => ({
  default: {
    MediaPlayer: () => ({
      create: mocks.create.mockReturnValue({
        initialize: mocks.initialize,
        reset: mocks.reset,
      }),
    }),
  },
}));

import { DashVideoEngine } from "./dash";

describe("DashVideoEngine", () => {
  it("initializes dash.js with the provided source", async () => {
    const video = {
      pause: vi.fn(),
      removeAttribute: vi.fn(),
      load: vi.fn(),
    } as unknown as HTMLVideoElement;
    const source = {
      url: "https://media.example.test/manifest.mpd",
      mime_type: "application/dash+xml",
    };
    const engine = new DashVideoEngine();

    await engine.attach(video, source);

    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(mocks.initialize).toHaveBeenCalledWith(video, source.url, false);
  });

  it("resets dash.js on detach", async () => {
    const video = {
      pause: vi.fn(),
      removeAttribute: vi.fn(),
      load: vi.fn(),
    } as unknown as HTMLVideoElement;
    const engine = new DashVideoEngine();

    await engine.attach(video, {
      url: "https://media.example.test/manifest.mpd",
      mime_type: "application/dash+xml",
    });
    engine.detach();

    expect(mocks.reset).toHaveBeenCalledTimes(1);
    expect(video.pause).toHaveBeenCalledTimes(1);
  });
});
