import { describe, expect, it } from "vitest";
import { releaseSearchQueryOptions } from "./useReleaseSearch";

describe("releaseSearchQueryOptions", () => {
  it("disables the query for an empty search", () => {
    const options = releaseSearchQueryOptions("");

    expect(options.enabled).toBe(false);
    expect(options.queryKey).toEqual(["releases", "search", ""]);
  });

  it("configures explicit no-retry behavior for manual searches", () => {
    const options = releaseSearchQueryOptions("Frieren 1080p");

    expect(options.enabled).toBe(true);
    expect(options.retry).toBe(false);
    expect(options.queryKey).toEqual([
      "releases",
      "search",
      "Frieren 1080p",
    ]);
  });
});
