import { describe, expect, it } from "vitest";
import { findThumbnailCue, parseThumbnailVtt } from "./thumbnail";

describe("parseThumbnailVtt", () => {
  it("parses WebVTT sprite coordinates", () => {
    const cues = parseThumbnailVtt(`WEBVTT

00:00:00.000 --> 00:00:05.000
sprite.jpg#xywh=0,0,160,90

00:00:05.000 --> 00:00:10.000
sprite.jpg#xywh=160,0,160,90
`);

    expect(cues).toEqual([
      {
        start_seconds: 0,
        end_seconds: 5,
        url: "sprite.jpg",
        x: 0,
        y: 0,
        width: 160,
        height: 90,
      },
      {
        start_seconds: 5,
        end_seconds: 10,
        url: "sprite.jpg",
        x: 160,
        y: 0,
        width: 160,
        height: 90,
      },
    ]);
  });
});

describe("findThumbnailCue", () => {
  const cues = [
    {
      start_seconds: 0,
      end_seconds: 5,
      url: "sprite.jpg",
      x: 0,
      y: 0,
      width: 160,
      height: 90,
    },
    {
      start_seconds: 5,
      end_seconds: 10,
      url: "sprite.jpg",
      x: 160,
      y: 0,
      width: 160,
      height: 90,
    },
  ];

  it("returns the cue containing the playback position", () => {
    expect(findThumbnailCue(cues, 6)).toEqual(cues[1]);
  });

  it("returns null for an invalid position", () => {
    expect(findThumbnailCue(cues, Number.NaN)).toBeNull();
  });
});
