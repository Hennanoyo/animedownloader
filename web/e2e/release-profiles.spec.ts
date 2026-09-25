import { expect, test } from "@playwright/test";

const GROUP_ID = "019a0000-0000-7000-8000-000000000020";
const PROFILE_ID = "019a0000-0000-7000-8000-000000000021";

const group = {
  id: GROUP_ID,
  name: "ExampleSubs",
  slug: "examplesubs",
  enabled: true,
  active_parser_profile_version: null,
  draft_parser_profile_version: 1,
};

const profile = {
  id: PROFILE_ID,
  release_group_id: GROUP_ID,
  release_group_name: group.name,
  version: 1,
  status: "draft",
  created_at: "2026-09-25T00:00:00Z",
  activated_at: null,
  rules: [
    {
      id: "019a0000-0000-7000-8000-000000000030",
      field: "release_group",
      pattern: "^\\[(?P<release_group>[^\\]]+)\\]",
      priority: 10,
      required: true,
      flags: "",
      transform: "identity",
    },
    {
      id: "019a0000-0000-7000-8000-000000000031",
      field: "episode_number",
      pattern: "(?P<episode_number>\\d{1,4})",
      priority: 20,
      required: true,
      flags: "",
      transform: "to_int",
    },
    {
      id: "019a0000-0000-7000-8000-000000000032",
      field: "resolution",
      pattern: "(?P<resolution>2160p|1080p|720p|480p)",
      priority: 30,
      required: false,
      flags: "i",
      transform: "identity",
    },
  ],
};

const samples = [
  {
    id: "019a0000-0000-7000-8000-000000000040",
    release_group_id: GROUP_ID,
    source: "nyaa",
    title: "[ExampleSubs] Frieren - 08 [1080p][HEVC].mkv",
    created_at: "2026-09-25T00:00:00Z",
    updated_at: "2026-09-25T00:00:00Z",
  },
  {
    id: "019a0000-0000-7000-8000-000000000041",
    release_group_id: GROUP_ID,
    source: "nyaa",
    title: "[ExampleSubs] Frieren - 09 [720p][HEVC].mkv",
    created_at: "2026-09-25T00:10:00Z",
    updated_at: "2026-09-25T00:10:00Z",
  },
];

const health = {
  profile_id: PROFILE_ID,
  total_count: 24,
  parsed_count: 22,
  ambiguous_count: 1,
  unparsed_count: 1,
  unsupported_count: 0,
  failure_rate: 2 / 24,
  drift_signal: false,
  drift_reason: null,
  recent_failures: [],
};

const comparison = {
  profile_id: PROFILE_ID,
  draft_version: 1,
  active_version: null,
  differences: [],
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/release-groups", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([group]),
    });
  });

  await page.route(
    `**/api/release-groups/${GROUP_ID}/parser-profiles`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([profile]),
      });
    },
  );

  await page.route(
    `**/api/release-groups/${GROUP_ID}/parser-samples`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(samples),
      });
    },
  );

  await page.route(
    `**/api/release-parser-profiles/${PROFILE_ID}/health`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(health),
      });
    },
  );

  await page.route(
    `**/api/release-parser-profiles/${PROFILE_ID}/comparison`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(comparison),
      });
    },
  );
});

test("renders release profile editor and remains usable without horizontal overflow", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/release-profiles");

  await expect(
    page.getByRole("heading", { name: "Release profiles" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Representative samples" }),
  ).toBeVisible();

  await expect(
    page.getByRole("checkbox", { name: "Rule 1 required" }),
  ).toBeChecked();
  await expect(
    page.getByRole("button", { name: "Rule 1 target field", exact: true }),
  ).toContainText("Release group");
  await expect(
    page.getByRole("button", { name: "Expand rule 1" }),
  ).toBeVisible();

  const firstPattern = page.getByRole("textbox", {
    name: "Rule 1 pattern",
  });
  await expect(firstPattern).toBeHidden();

  await page.getByRole("button", { name: "Expand rule 1" }).click();
  await expect(
    page.getByRole("button", { name: "Collapse rule 1" }),
  ).toBeVisible();
  await expect(firstPattern).toHaveAttribute(
    "placeholder",
    "^\\[(?P<release_group>[^\\]]+)\\]",
  );

  const patternHelp = page.getByRole("button", {
    name: "Rule 1 regex pattern help",
  });
const tooltip = page.getByRole("tooltip");

  await patternHelp.hover();
  await expect(tooltip).toBeVisible();
  await expect(tooltip).toContainText("How regex matching works");
  await expect(tooltip).toContainText(
    "Example: [ExampleSubs] Frieren - 08 → ExampleSubs",
  );

  await patternHelp.blur();
  await page.getByRole("heading", { name: "Release profiles" }).hover();
  await expect(tooltip).toBeHidden({ timeout: 1000 });

  await patternHelp.focus();
  await expect(tooltip).toBeVisible();
  await page.getByRole("heading", { name: "Release profiles" }).hover();
  await expect(tooltip).toBeHidden({ timeout: 1000 });

  const targetField = page.getByRole("button", {
    name: "Rule 1 target field",
    exact: true,
  });
  await expect(targetField).toHaveCSS("min-height", "38.4px");

  const sampleInput = page.getByRole("textbox", {
    name: "Sample release title",
  });
  await expect(sampleInput).toHaveCSS("min-height", "38.4px");

  await page.getByRole("button", {
    name: "Rule 1 transform",
    exact: true,
  }).click();
  await expect(
    page.getByRole("option", { name: "Convert to integer" }),
  ).toBeVisible();
  await expect(
    page.getByRole("option", { name: "Normalize spaces" }),
  ).toBeVisible();

  await expect(
    page.getByRole("button", {
      name: "Delete sample [ExampleSubs] Frieren - 08 [1080p][HEVC].mkv",
    }),
  ).toBeVisible();

  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    )
    .toBe(true);

  await testInfo.attach("release-profiles-desktop", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });

  await page.setViewportSize({ width: 390, height: 900 });
  await page.waitForTimeout(100);

  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    )
    .toBe(true);

  await testInfo.attach("release-profiles-mobile", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
});
