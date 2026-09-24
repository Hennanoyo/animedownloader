import { describe, expect, it, vi } from "vitest";

const hls = vi.hoisted(() => ({
  isSupported: vi.fn(() => true),
}));

vi.mock("hls.js", () => ({
  default: {
    isSupported: hls.isSupported,
  },
}));

vi.mock("dashjs", () => ({
  default: {
    MediaPlayer: () => ({
      create: vi.fn(),
    }),
  },
}));

import { selectVideoEngine } from "./select";

function makeVideo(canPlayType: (mimeType: string) => string) {
  return {
    canPlayType,
  } as unknown as HTMLVideoElement;
}

const sources = {
  direct: {
    url: "https://media.example.test/direct.mp4",
    mime_type: "video/mp4",
  },
  hls: {
    url: "https://media.example.test/master.m3u8",
    mime_type: "application/vnd.apple.mpegurl",
  },
  dash: {
    url: "https://media.example.test/manifest.mpd",
    mime_type: "application/dash+xml",
  },
};

describe("selectVideoEngine", () => {
  it("prefers HLS.js when supported", () => {
    hls.isSupported.mockReturnValue(true);

    const selected = selectVideoEngine(makeVideo(() => ""), sources);

    expect(selected?.source.kind).toBe("hls");
  });

  it("falls back to native HLS when HLS.js is unavailable", () => {
    hls.isSupported.mockReturnValue(false);

    const selected = selectVideoEngine(
      makeVideo((mimeType) =>
        mimeType === "application/vnd.apple.mpegurl" ? "maybe" : "",
      ),
      sources,
    );

    expect(selected?.source.kind).toBe("hls");
  });

  it("uses DASH when HLS is unavailable and MediaSource exists", () => {
    hls.isSupported.mockReturnValue(false);

    const selected = selectVideoEngine(makeVideo(() => ""), {
      direct: sources.direct,
      hls: null,
      dash: sources.dash,
    });

    expect(selected?.source.kind).toBe("dash");
  });

  it("falls back to direct MP4", () => {
    hls.isSupported.mockReturnValue(false);

    const selected = selectVideoEngine(makeVideo(() => ""), {
      direct: sources.direct,
      hls: null,
      dash: null,
    });

    expect(selected?.source.kind).toBe("direct");
  });
});
