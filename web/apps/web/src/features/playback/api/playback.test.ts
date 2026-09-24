import { describe, expect, it, vi } from "vitest";
import { getPlayback, PlaybackResponseError } from "./playback";

const payload = {
  anime_id: "0198a2a8-5b7c-7d7d-8a1f-9f0b8d53f000",
  episode_id: "0198a2a8-5b7c-7d7d-8a1f-9f0b8d53f001",
  episode_number: 1,
  title: "Episode 01",
  duration_seconds: 12,
  video: {
    direct: {
      url: "http://localhost:8888/playable/asset/variant.mp4",
      mime_type: "video/mp4",
    },
    hls: {
      url: "http://localhost:8888/streaming/package/master.m3u8",
      mime_type: "application/vnd.apple.mpegurl",
    },
    dash: {
      url: "http://localhost:8888/streaming/package/manifest.mpd",
      mime_type: "application/dash+xml",
    },
  },
  subtitles: [],
  fonts: [],
  chapters: [],
  thumbnails: null,
};

describe("playback API", () => {
  it("parses a valid playback response", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getPlayback(payload.episode_id);

    expect(result).toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/episodes/" +
        payload.episode_id +
        "/playback",
      expect.objectContaining({ method: "GET" }),
    );
    vi.unstubAllGlobals();
  });

  it("rejects an invalid playback response", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ episode_id: "invalid" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getPlayback(payload.episode_id)).rejects.toBeInstanceOf(
      PlaybackResponseError,
    );

    vi.unstubAllGlobals();
  });
});
