import { describe, expect, it } from "vitest";
import { animePipelineQueryOptions } from "./useAnimePipeline";

describe("anime pipeline query", () => {
  it("polls only while at least one episode is active", () => {
    const options = animePipelineQueryOptions(
      "019a0000-0000-7000-8000-000000000001",
    );

    expect(options.refetchOnMount).toBe("always");
    expect(options.refetchOnWindowFocus).toBe(false);
    expect(options.refetchInterval?.({ state: { data: undefined } } as never)).toBe(
      false,
    );
    expect(
      options.refetchInterval?.({
        state: {
          data: {
            anime_id: "019a0000-0000-7000-8000-000000000001",
            episodes: [
              {
                active: true,
                episode_id: "019a0000-0000-7000-8000-000000000002",
              },
            ],
          },
        },
      } as never),
    ).toBe(2000);
  });
});
