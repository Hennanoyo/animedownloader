import { describe, expect, it } from "vitest";
import { getApiBaseUrl } from "./api";

describe("getApiBaseUrl", () => {
  it("uses the development API when no URL is configured", () => {
    expect(getApiBaseUrl(undefined)).toBe("http://localhost:8000");
  });

  it("removes a trailing slash", () => {
    expect(getApiBaseUrl("https://api.example.com/")).toBe("https://api.example.com");
  });
});
