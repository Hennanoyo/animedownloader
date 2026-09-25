import { expect, test } from "@playwright/test";

const EPISODE_ACTIVE = "019a0000-0000-7000-8000-000000000010";
const EPISODE_FAILED = "019a0000-0000-7000-8000-000000000020";
const JOB_ACTIVE = "019a0000-0000-7000-8000-000000000011";
const JOB_FAILED = "019a0000-0000-7000-8000-000000000021";
const ANIME_ID = "019a0000-0000-7000-8000-000000000030";

let activeStatus: "downloading" | "paused" | "cancelled" = "downloading";
let historyDeleted = false;
let downloadListRequests = 0;

function makeActiveJob(
  status: "downloading" | "paused" | "cancelled",
) {
  return {
    id: JOB_ACTIVE,
    episode_id: EPISODE_ACTIVE,
    anime_id: ANIME_ID,
    anime_title: "Browser Download Anime",
    episode_number: 1,
    episode_title: "Episode One",
    status,
    downloaded_bytes: status === "cancelled" ? 700 : 500,
    total_bytes: 1000,
    attempt_count: 1,
    error_message: null,
    started_at: "2026-09-25T00:00:00Z",
    completed_at:
      status === "cancelled" ? "2026-09-25T00:10:00Z" : null,
    created_at: "2026-09-25T00:00:00Z",
    updated_at: "2026-09-25T00:05:00Z",
  };
}

const failedJob = {
  id: JOB_FAILED,
  episode_id: EPISODE_FAILED,
  anime_id: ANIME_ID,
  anime_title: "Browser Download Anime",
  episode_number: 2,
  episode_title: "Episode Two",
  status: "failed",
  downloaded_bytes: 200,
  total_bytes: 1000,
  attempt_count: 2,
  error_message: "qBittorrent reported an error.",
  started_at: "2026-09-25T00:00:00Z",
  completed_at: null,
  created_at: "2026-09-25T00:01:00Z",
  updated_at: "2026-09-25T00:06:00Z",
};

const historyJob = {
  ...failedJob,
  status: "completed",
  error_message: null,
  completed_at: "2026-09-25T00:10:00Z",
};

test.beforeEach(async ({ page }) => {
  activeStatus = "downloading";
  historyDeleted = false;
  downloadListRequests = 0;

  await page.route("**/api/download-jobs?*", async (route) => {
    downloadListRequests += 1;
    const url = new URL(route.request().url());
    const statuses = url.searchParams.getAll("status");

    if (
      statuses.includes("pending") ||
      statuses.includes("downloading") ||
      statuses.includes("paused")
    ) {
      const items =
        activeStatus === "cancelled" ? [] : [makeActiveJob(activeStatus)];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items,
          page: 1,
          page_size: 100,
          total: items.length,
          has_more: false,
        }),
      });
      return;
    }

    if (statuses.includes("completed") || statuses.includes("cancelled")) {
      const items = historyDeleted ? [] : [historyJob];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items,
          page: 1,
          page_size: 100,
          total: items.length,
          has_more: false,
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [failedJob],
        page: 1,
        page_size: 100,
        total: 1,
        has_more: false,
      }),
    });
  });

  await page.route(
    `**/api/download-jobs/${JOB_ACTIVE}/pause`,
    async (route) => {
      activeStatus = "paused";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(makeActiveJob("paused")),
      });
    },
  );

  await page.route(
    `**/api/download-jobs/${JOB_ACTIVE}/resume`,
    async (route) => {
      activeStatus = "downloading";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(makeActiveJob("downloading")),
      });
    },
  );

  await page.route(
    `**/api/download-jobs/${JOB_ACTIVE}/cancel`,
    async (route) => {
      activeStatus = "cancelled";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(makeActiveJob("cancelled")),
      });
    },
  );

  await page.route(
    `**/api/download-jobs/${JOB_FAILED}`,
    async (route) => {
      if (route.request().method() === "DELETE") {
        historyDeleted = true;
        await route.fulfill({ status: 204 });
        return;
      }
      await route.continue();
    },
  );
});

test("manages active download and terminal filters", async ({ page }) => {
  await page.goto("/downloads");

  await expect(page.getByRole("heading", { name: "Downloads" })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Browser Download Anime", exact: true }),
  ).toHaveCount(2);
  await expect(
    page.locator('article[data-status="downloading"]'),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Pause download for Episode One" }),
  ).toBeVisible();

  await page
    .getByRole("button", { name: "Pause download for Episode One" })
    .click();
  await expect(
    page.locator('article[data-status="paused"]'),
  ).toBeVisible();

  await page
    .getByRole("button", { name: "Cancel download for Episode One" })
    .click();
  await expect(
    page.getByRole("alertdialog", {
      name: "Cancel download for Episode One",
    }),
  ).toBeVisible();
  await page
    .getByRole("alertdialog", {
      name: "Cancel download for Episode One",
    })
    .getByRole("button", { name: "Cancel download", exact: true })
    .click();
  await expect(
    page.getByText("No downloads are currently active."),
  ).toBeVisible();

  await page.getByRole("link", { name: "Failed" }).click();
  await expect(
    page.getByRole("heading", { name: "Failed", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("qBittorrent reported an error.")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Retry Episode Two" }),
  ).toBeVisible();
});

test("receives live progress without polling while realtime is healthy", async ({ page }) => {
  await page.addInitScript(() => {
    class MockWebSocket {
      static instances: MockWebSocket[] = [];
      readonly url: string;
      readyState = 0;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onclose: ((event: Event) => void) | null = null;

      constructor(url: string) {
        this.url = url;
        MockWebSocket.instances.push(this);
        setTimeout(() => {
          this.readyState = 1;
          this.onopen?.(new Event("open"));
          this.onmessage?.(
            new MessageEvent("message", {
              data: JSON.stringify({
                version: 1,
                type: "job.ready",
                job_type: "download",
                emitted_at: "2026-09-25T00:00:00Z",
              }),
            }),
          );
        }, 0);
      }

      close() {
        if (this.readyState === 3) {
          return;
        }
        this.readyState = 3;
        this.onclose?.(new Event("close"));
      }

      emit(payload: unknown) {
        this.onmessage?.(
          new MessageEvent("message", {
            data: JSON.stringify(payload),
          }),
        );
      }
    }

    Object.defineProperty(globalThis, "WebSocket", {
      configurable: true,
      value: MockWebSocket,
    });
    Object.defineProperty(window, "__emitDownloadEvent", {
      configurable: true,
      value: (payload: unknown) => {
        MockWebSocket.instances.at(-1)?.emit(payload);
      },
    });
  });

  await page.goto("/downloads");
  await expect(
    page.locator('article[data-status="downloading"]'),
  ).toBeVisible();

  await page.waitForTimeout(1000);
  const requestsAfterRealtimeConnect = downloadListRequests;

  await page.evaluate(() => {
    const windowWithEmitter = window as Window & {
      __emitDownloadEvent: (payload: unknown) => void;
    };
    windowWithEmitter.__emitDownloadEvent({
      version: 1,
      type: "job.progress",
      job_type: "download",
      job_id: JOB_ACTIVE,
      status: "downloading",
      progress_percent: 65,
      downloaded_bytes: 650,
      total_bytes: 1000,
      error_message: null,
      emitted_at: "2026-09-25T00:01:00Z",
    });
  });

  await expect(page.getByText("650 B / 1000 B", { exact: true })).toBeVisible();
  await page.waitForTimeout(2500);
  expect(downloadListRequests).toBe(requestsAfterRealtimeConnect);
});

test("renders history and delete confirmation", async ({ page }) => {
  await page.goto("/downloads?status=history");

  await expect(
    page.getByRole("heading", { name: "History", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Download again Episode Two" }),
  ).toBeVisible();

  await page
    .getByRole("button", {
      name: "Delete download record for Episode Two",
    })
    .click();
  await expect(
    page.getByRole("alertdialog", {
      name: "Delete download record for Episode Two",
    }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Delete record" }).click();
  await expect(
    page.getByText("No completed or cancelled downloads yet."),
  ).toBeVisible();
});

test("does not create horizontal overflow on a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/downloads");

  const widths = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));

  expect(widths.document).toBeLessThanOrEqual(widths.viewport);
});
