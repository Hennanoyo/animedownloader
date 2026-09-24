import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  isSupported: vi.fn(() => true),
  loadSource: vi.fn(),
  attachMedia: vi.fn(),
  destroy: vi.fn(),
}));

vi.mock("hls.js", () => ({
  default: class Hls {
    static isSupported = mocks.isSupported;
    loadSource = mocks.loadSource;
    attachMedia = mocks.attachMedia;
    destroy = mocks.destroy;
  },
}));

import { HlsVideoEngine } from "./hls";

describe("HlsVideoEngine", () => {
  it("loads and attaches an HLS source", async () => {
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

    expect(mocks.loadSource).toHaveBeenCalledWith(source.url);
    expect(mocks.attachMedia).toHaveBeenCalledWith(video);
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
