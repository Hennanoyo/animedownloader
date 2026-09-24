import { describe, expect, it } from "vitest";
import { playbackQueryOptions } from "./usePlayback";

describe("playback query", () => {
  it("refreshes playback when the player mounts", () => {
    const options = playbackQueryOptions(
      "0198a2a8-5b7c-7d7d-8a1f-9f0b8d53f001",
    );

    expect(options.retry).toBe(1);
    expect(options.staleTime).toBe(30_000);
    expect(options.refetchOnMount).toBe("always");
    expect(options.refetchOnWindowFocus).toBe(false);
  });
});
