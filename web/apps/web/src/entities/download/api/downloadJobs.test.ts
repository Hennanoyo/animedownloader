import { describe, expect, it, vi } from "vitest";
import {
  cancelDownloadJob,
  createEpisodeDownloadJob,
  deleteDownloadJob,
  getLatestEpisodeDownloadJob,
  pauseDownloadJob,
  resumeDownloadJob,
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


  it("controls and deletes a download job", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      const status =
        url.endsWith("/pause") ? "paused" :
        url.endsWith("/resume") ? "downloading" :
        url.endsWith("/cancel") ? "cancelled" :
        jobPayload.status;
      return new Response(
        method === "DELETE" ? null : JSON.stringify({ ...jobPayload, status }),
        { status: method === "DELETE" ? 204 : 200 },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    expect((await pauseDownloadJob(jobPayload.id)).status).toBe("paused");
    expect((await resumeDownloadJob(jobPayload.id)).status).toBe("downloading");
    expect((await cancelDownloadJob(jobPayload.id)).status).toBe("cancelled");
    await deleteDownloadJob(jobPayload.id);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/download-jobs/" + jobPayload.id + "/pause"),
      expect.objectContaining({ method: "POST", body: "{}" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/download-jobs/" + jobPayload.id),
      expect.objectContaining({ method: "DELETE" }),
    );
    vi.unstubAllGlobals();
  });
