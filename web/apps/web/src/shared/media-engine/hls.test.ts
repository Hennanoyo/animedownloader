import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  isSupported: vi.fn(() => true),
  loadSource: vi.fn(),
  attachMedia: vi.fn(),
  on: vi.fn(),
  once: vi.fn(),
  off: vi.fn(),
  startLoad: vi.fn(),
  recoverMediaError: vi.fn(),
  destroy: vi.fn(),
  errorHandler: null as
    | ((event: string, data: {
        fatal?: boolean;
        type?: string;
        details?: string;
      }) => void)
    | null,
}));

vi.mock("hls.js", () => ({
  default: class Hls {
    static isSupported = mocks.isSupported;
    static Events = {
      ERROR: "hlsError",
      MEDIA_ATTACHED: "hlsMediaAttached",
    };
    static ErrorTypes = {
      NETWORK_ERROR: "networkError",
      MEDIA_ERROR: "mediaError",
    };
    loadSource = mocks.loadSource;
    attachMedia = mocks.attachMedia;
    on = mocks.on.mockImplementation(
      (
        _event: string,
        callback: (event: string, data: {
          fatal?: boolean;
          type?: string;
          details?: string;
        }) => void,
      ) => {
        mocks.errorHandler = callback;
      },
    );
    once = mocks.once.mockImplementation(
      (_event: string, callback: () => void) => {
        callback();
      },
    );
    off = mocks.off;
    startLoad = mocks.startLoad;
    recoverMediaError = mocks.recoverMediaError;
    destroy = mocks.destroy;
  },
}));

import { HlsVideoEngine } from "./hls";

describe("HlsVideoEngine", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.errorHandler = null;
  });
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

  it("recovers one fatal network error before reporting a second one", async () => {
    const video = {
      pause: vi.fn(),
      removeAttribute: vi.fn(),
      load: vi.fn(),
    } as unknown as HTMLVideoElement;
    const onError = vi.fn();
    const engine = new HlsVideoEngine();

    await engine.attach(
      video,
      {
        url: "https://media.example.test/master.m3u8",
        mime_type: "application/vnd.apple.mpegurl",
      },
      { onError },
    );

    mocks.errorHandler?.("error", {
      fatal: true,
      type: "networkError",
      details: "MANIFEST_LOAD_ERROR",
    });
    expect(mocks.startLoad).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();

    mocks.errorHandler?.("error", {
      fatal: true,
      type: "networkError",
      details: "MANIFEST_LOAD_ERROR",
    });
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining("MANIFEST_LOAD_ERROR"),
      }),
    );
  });

  it("recovers one fatal media error before reporting a second one", async () => {
    const video = {
      pause: vi.fn(),
      removeAttribute: vi.fn(),
      load: vi.fn(),
    } as unknown as HTMLVideoElement;
    const onError = vi.fn();
    const engine = new HlsVideoEngine();

    await engine.attach(
      video,
      {
        url: "https://media.example.test/master.m3u8",
        mime_type: "application/vnd.apple.mpegurl",
      },
      { onError },
    );

    mocks.errorHandler?.("error", {
      fatal: true,
      type: "mediaError",
      details: "BUFFER_INCOMPATIBLE_CODECS_ERROR",
    });
    expect(mocks.recoverMediaError).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();

    mocks.errorHandler?.("error", {
      fatal: true,
      type: "mediaError",
      details: "BUFFER_INCOMPATIBLE_CODECS_ERROR",
    });
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining("BUFFER_INCOMPATIBLE_CODECS_ERROR"),
      }),
    );
  });

  it("ignores non-fatal HLS errors", async () => {
    const video = {
      pause: vi.fn(),
      removeAttribute: vi.fn(),
      load: vi.fn(),
    } as unknown as HTMLVideoElement;
    const onError = vi.fn();
    const engine = new HlsVideoEngine();

    await engine.attach(
      video,
      {
        url: "https://media.example.test/master.m3u8",
        mime_type: "application/vnd.apple.mpegurl",
      },
      { onError },
    );

    mocks.errorHandler?.("error", {
      fatal: false,
      type: "networkError",
      details: "FRAG_LOAD_TIMEOUT",
    });

    expect(onError).not.toHaveBeenCalled();
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
    expect(video.removeAttribute).toHaveBeenCalled();
  });
});
