import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  reset: vi.fn(),
  initialize: vi.fn(),
  create: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  errorHandler: null as ((event: unknown) => void) | null,
}));

vi.mock("dashjs", () => ({
  MediaPlayer: Object.assign(
    () => ({
      create: mocks.create.mockReturnValue({
        initialize: mocks.initialize,
        reset: mocks.reset,
        on: mocks.on.mockImplementation(
          (_event: string, callback: (event: unknown) => void) => {
            mocks.errorHandler = callback;
          },
        ),
        off: mocks.off,
      }),
    }),
    {
      events: {
        ERROR: "error",
      },
    },
  ),
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
    expect(mocks.on).toHaveBeenCalledWith("error", expect.any(Function));
  });

  it("reports dash.js errors", async () => {
    const video = {
      pause: vi.fn(),
      removeAttribute: vi.fn(),
      load: vi.fn(),
    } as unknown as HTMLVideoElement;
    const onError = vi.fn();
    const engine = new DashVideoEngine();

    await engine.attach(
      video,
      {
        url: "https://media.example.test/manifest.mpd",
        mime_type: "application/dash+xml",
      },
      { onError },
    );

    mocks.errorHandler?.({
      error: { message: "manifest failed" },
    });

    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining("manifest failed"),
      }),
    );
  });

  it("removes dash.js error listener and resets on detach", async () => {
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

    expect(mocks.off).toHaveBeenCalledWith("error", expect.any(Function));
    expect(mocks.reset).toHaveBeenCalledTimes(1);
    expect(video.pause).toHaveBeenCalledTimes(1);
  });
});
