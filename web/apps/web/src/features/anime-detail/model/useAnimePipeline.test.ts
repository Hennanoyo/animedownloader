import { describe, expect, it } from "vitest";
import {
  animePipelineQueryOptions,
  getAnimePipelineRefetchInterval,
} from "./useAnimePipeline";

describe("anime pipeline query", () => {
  it("polls only while at least one episode is active", () => {
    expect(getAnimePipelineRefetchInterval(undefined)).toBe(false);
    expect(
      getAnimePipelineRefetchInterval({
        episodes: [],
      }),
    ).toBe(false);
    expect(
      getAnimePipelineRefetchInterval({
        episodes: [{ active: true }],
      }),
    ).toBe(2000);
  });

  it("stops polling while realtime is connected", () => {
    expect(
      getAnimePipelineRefetchInterval(
        { episodes: [{ active: true }] },
        true,
      ),
    ).toBe(false);
  });

  it("keeps pipeline queries independent of window focus", () => {
    const options = animePipelineQueryOptions(
      "019a0000-0000-7000-8000-000000000001",
    );

    expect(options.refetchOnMount).toBe("always");
    expect(options.refetchOnWindowFocus).toBe(false);
  });
});
