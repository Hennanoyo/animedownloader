import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  isSupported: vi.fn(() => true),
  loadSource: vi.fn(),
  attachMedia: vi.fn(),
  once: vi.fn(),
  destroy: vi.fn(),
}));

vi.mock("hls.js", () => ({
  default: class Hls {
    static isSupported = mocks.isSupported;
    static Events = {
      MEDIA_ATTACHED: "hlsMediaAttached",
    };
    loadSource = mocks.loadSource;
    attachMedia = mocks.attachMedia;
    once = mocks.once.mockImplementation(
      (_event: string, callback: () => void) => {
        callback();
      },
    );
    destroy = mocks.destroy;
  },
}));

import { HlsVideoEngine } from "./hls";

describe("HlsVideoEngine", () => {
  it("loads the HLS source after media is attached", async () => {
    const video = {
      pause: vi.fn(),
      removeAttribute: vi.fn(),
      load: vi.fn(),
    } as unknown as HTMLVideoElement;
    const source = {
      url: "https://media.example.test/master.m3u8",
      mime_type: "application/vnd.apple.mpegurl",
    };
    const engine = new HlsVideoEngine();

    await engine.attach(video, source);

    expect(mocks.attachMedia).toHaveBeenCalledWith(video);
    expect(mocks.once).toHaveBeenCalledWith(
      "hlsMediaAttached",
      expect.any(Function),
    );
    expect(mocks.loadSource).toHaveBeenCalledWith(source.url);
  });

  it("destroys the HLS instance on detach", async () => {
    const video = {
      pause: vi.fn(),
      removeAttribute: vi.fn(),
      load: vi.fn(),
    } as unknown as HTMLVideoElement;
    const engine = new HlsVideoEngine();

    await engine.attach(video, {
      url: "https://media.example.test/master.m3u8",
      mime_type: "application/vnd.apple.mpegurl",
    });
    engine.detach();

    expect(mocks.destroy).toHaveBeenCalledTimes(1);
    expect(video.pause).toHaveBeenCalledTimes(1);
    expect(video.removeAttribute).toHaveBeenCalledWith("src");
  });
});
