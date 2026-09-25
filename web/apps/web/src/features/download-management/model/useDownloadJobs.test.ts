import { describe, expect, it } from "vitest";
import {
  activeDownloadStatuses,
  downloadJobsQueryOptions,
  getDownloadJobsRefetchInterval,
} from "./useDownloadJobs";

const item = {
  id: "019a0000-0000-7000-8000-000000000001",
  episode_id: "019a0000-0000-7000-8000-000000000002",
  anime_id: "019a0000-0000-7000-8000-000000000003",
  anime_title: "Frieren",
  episode_number: 18,
  episode_title: "Episode 18",
  status: "downloading" as const,
  downloaded_bytes: 500,
  total_bytes: 1000,
  attempt_count: 1,
  error_message: null,
  started_at: new Date("2026-09-25T00:00:00Z"),
  completed_at: null,
  created_at: new Date("2026-09-25T00:00:00Z"),
  updated_at: new Date("2026-09-25T00:05:00Z"),
};

describe("download management query", () => {
  it("polls while a download can change on its own", () => {
    expect(
      getDownloadJobsRefetchInterval(undefined, activeDownloadStatuses),
    ).toBe(false);
    expect(
      getDownloadJobsRefetchInterval(
        {
          items: [],
          page: 1,
          page_size: 100,
          total: 0,
          has_more: false,
        },
        activeDownloadStatuses,
      ),
    ).toBe(false);
    expect(
      getDownloadJobsRefetchInterval(
        {
          items: [item],
          page: 1,
          page_size: 100,
          total: 1,
          has_more: false,
        },
        activeDownloadStatuses,
      ),
    ).toBe(2000);
  });

  it("does not poll paused-only data", () => {
    expect(
      getDownloadJobsRefetchInterval(
        {
          items: [{ ...item, status: "paused" as const }],
          page: 1,
          page_size: 100,
          total: 1,
          has_more: false,
        },
        activeDownloadStatuses,
      ),
    ).toBe(false);
  });

  it("never polls terminal-only lists", () => {
    expect(
      getDownloadJobsRefetchInterval(
        {
          items: [],
          page: 1,
          page_size: 100,
          total: 0,
          has_more: false,
        },
        ["completed", "failed", "cancelled"],
      ),
    ).toBe(false);
  });

  it("disables focus refetching", () => {
    const options = downloadJobsQueryOptions({
      statuses: activeDownloadStatuses,
    });
    expect(options.refetchOnWindowFocus).toBe(false);
  });
});
