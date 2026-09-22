import { describe, expect, it, vi } from "vitest";
import { ApiRequestError, getJson } from "./client";

describe("getJson", () => {
  it("returns parsed JSON for a successful response", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getJson("/api/health")).resolves.toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/health",
      expect.objectContaining({ method: "GET" }),
    );

    vi.unstubAllGlobals();
  });

  it("includes the HTTP status and API detail for failed responses", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Nyaa search is temporarily unavailable" }),
        { status: 502 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getJson("/api/releases/search?q=Frieren")).rejects.toEqual(
      expect.objectContaining({
        name: "ApiRequestError",
        status: 502,
        message:
          "API request failed with status 502: Nyaa search is temporarily unavailable",
      }),
    );

    vi.unstubAllGlobals();
  });

  it("distinguishes network failures", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockRejectedValue(
      new TypeError("Failed to fetch"),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getJson("/api/health")).rejects.toThrow(
      "Network request failed: Failed to fetch",
    );

    vi.unstubAllGlobals();
  });

  it("preserves the custom API error type", () => {
    const error = new ApiRequestError("failed", 500, "oops");

    expect(error).toBeInstanceOf(Error);
    expect(error.status).toBe(500);
    expect(error.responseBody).toBe("oops");
  });
});
