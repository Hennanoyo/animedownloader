import { describe, expect, it } from "vitest";
import { animeEditFormSchema } from "./schema";

const validValues = {
  title: "Frieren: Beyond Journey's End",
  year: 2026,
  season: "fall",
  weekday: "friday",
  air_time: "23:00",
  timezone: "Asia/Tokyo",
};

describe("anime edit form schema", () => {
  it("accepts valid anime metadata", () => {
    expect(animeEditFormSchema.safeParse(validValues).success).toBe(true);
  });

  it("rejects empty titles", () => {
    const result = animeEditFormSchema.safeParse({
      ...validValues,
      title: "   ",
    });

    expect(result.success).toBe(false);
  });

  it("accepts an empty air time", () => {
    expect(
      animeEditFormSchema.safeParse({
        ...validValues,
        air_time: "",
      }).success,
    ).toBe(true);
  });

  it("rejects malformed air times", () => {
    const result = animeEditFormSchema.safeParse({
      ...validValues,
      air_time: "25:99",
    });

    expect(result.success).toBe(false);
  });
});
