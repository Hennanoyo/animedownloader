import { describe, expect, it, vi } from "vitest";
import {
  ApiRequestError,
  deleteJson,
  getJson,
  patchJson,
  postJson,
} from "./client";

describe("api client", () => {
  it("handles successful GET requests", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getJson("/api/health")).resolves.toEqual({ status: "ok" });
    vi.unstubAllGlobals();
  });

  it("sends JSON POST and PATCH bodies", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async () => {
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await postJson("/api/animes", { title: "Frieren" });
    await patchJson("/api/animes/1", { title: "Updated" });

    expect(fetchMock.mock.calls[0]?.[1]).toEqual(
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock.mock.calls[1]?.[1]).toEqual(
      expect.objectContaining({ method: "PATCH" }),
    );
    vi.unstubAllGlobals();
  });

  it("accepts empty DELETE responses", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(null, { status: 204 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(deleteJson("/api/animes/1")).resolves.toBeUndefined();
    vi.unstubAllGlobals();
  });

  it("exposes API error details", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not found" }), { status: 404 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getJson("/api/animes/1")).rejects.toEqual(
      expect.objectContaining({
        name: "ApiRequestError",
        status: 404,
        message: "API request failed with status 404: Not found",
      }),
    );
    vi.unstubAllGlobals();
  });

  it("preserves the response body on ApiRequestError", () => {
    const error = new ApiRequestError("failed", 500, "oops");
    expect(error.responseBody).toBe("oops");
  });
});
