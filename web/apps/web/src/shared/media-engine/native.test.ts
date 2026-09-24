import { describe, expect, it, vi } from "vitest";
import { selectNativeSource, NativeVideoEngine } from "./native";

function makeVideo(canPlayType: (mimeType: string) => string) {
  return {
    canPlayType,
    load: vi.fn(),
    pause: vi.fn(),
    removeAttribute: vi.fn(),
    src: "",
  } as unknown as HTMLVideoElement;
}

describe("selectNativeSource", () => {
  it("prefers natively supported HLS", () => {
    const video = makeVideo((mimeType) =>
      mimeType === "application/vnd.apple.mpegurl" ? "probably" : "",
    );
    const direct = {
      url: "https://media.example.test/direct.mp4",
      mime_type: "video/mp4",
    };
    const hls = {
      url: "https://media.example.test/master.m3u8",
      mime_type: "application/vnd.apple.mpegurl",
    };

    expect(selectNativeSource(video, { direct, hls, dash: null })).toEqual({
      kind: "hls",
      source: hls,
    });
  });

  it("falls back to direct MP4", () => {
    const video = makeVideo(() => "");
    const direct = {
      url: "https://media.example.test/direct.mp4",
      mime_type: "video/mp4",
    };

    expect(selectNativeSource(video, { direct, hls: null, dash: null })).toEqual({
      kind: "direct",
      source: direct,
    });
  });

  it("returns null when no native source exists", () => {
    const video = makeVideo(() => "");
    expect(
      selectNativeSource(video, { direct: null, hls: null, dash: null }),
    ).toBeNull();
  });
});

describe("NativeVideoEngine", () => {
  it("attaches and detaches a source", async () => {
    const video = makeVideo(() => "");
    const engine = new NativeVideoEngine();
    const source = {
      url: "https://media.example.test/direct.mp4",
      mime_type: "video/mp4",
    };

    await engine.attach(video, source);

    expect(video.src).toBe(source.url);
    expect(video.load).toHaveBeenCalledTimes(1);

    engine.detach();

    expect(video.pause).toHaveBeenCalledTimes(1);
    expect(video.removeAttribute).toHaveBeenCalledWith("src");
    expect(video.load).toHaveBeenCalledTimes(2);
  });
});
