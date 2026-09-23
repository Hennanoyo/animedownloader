import { describe, expect, it, vi } from "vitest";
import {
  createEpisodeDownloadJob,
  getLatestEpisodeDownloadJob,
} from "./downloadJobs";

const jobPayload = {
  id: "0198a2a8-5b7c-7d7d-8a1f-9f0b8d53f000",
  episode_id: "0198a2a8-5b7c-7d7d-8a1f-9f0b8d53f001",
  status: "downloading",
  downloaded_bytes: 512,
  total_bytes: 1024,
  attempt_count: 1,
  error_message: null,
  started_at: "2026-09-23T00:00:00Z",
  completed_at: null,
  created_at: "2026-09-23T00:00:00Z",
  updated_at: "2026-09-23T00:00:05Z",
};

describe("download job API", () => {
  it("gets the latest download job for an episode", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(jobPayload), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getLatestEpisodeDownloadJob(jobPayload.episode_id);

    expect(result?.status).toBe("downloading");
    expect(result?.downloaded_bytes).toBe(512);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        "/api/episodes/" + jobPayload.episode_id + "/download-jobs/latest",
      ),
      expect.objectContaining({ method: "GET" }),
    );
    vi.unstubAllGlobals();
  });

  it("returns null when an episode has no download job", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response("null", { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getLatestEpisodeDownloadJob(jobPayload.episode_id);

    expect(result).toBeNull();
    vi.unstubAllGlobals();
  });

  it("creates a download job", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(jobPayload), { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await createEpisodeDownloadJob(jobPayload.episode_id);

    expect(result.id).toBe(jobPayload.id);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        "/api/episodes/" + jobPayload.episode_id + "/download-jobs",
      ),
      expect.objectContaining({
        method: "POST",
        body: "{}",
      }),
    );
    vi.unstubAllGlobals();
  });
});
