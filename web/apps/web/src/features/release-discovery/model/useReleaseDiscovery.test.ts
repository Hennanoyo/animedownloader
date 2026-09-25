import { describe, expect, it } from "vitest";
import { releaseDiscoveryQueryOptions } from "./useReleaseDiscovery";

describe("releaseDiscoveryQueryOptions", () => {
  it("disables discovery before a search is submitted", () => {
    const options = releaseDiscoveryQueryOptions(null);

    expect(options.enabled).toBe(false);
    expect(options.queryKey).toEqual(["releases", "discover", null]);
  });

  it("uses all discovery constraints as a stable query key", () => {
    const input = {
      title: "Frieren",
      fields: ["group", "title", "episode", "resolution", "codec"] as const,
      group: "ExampleSubs",
      episode: 8,
      resolution: "1080p",
      codec: "HEVC",
    };
    const options = releaseDiscoveryQueryOptions(input);

    expect(options.enabled).toBe(true);
    expect(options.retry).toBe(false);
    expect(options.queryKey).toEqual(["releases", "discover", input]);
  });
});
