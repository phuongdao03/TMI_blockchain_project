import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { BrowserContext, Page } from "@playwright/test";

const mockApiUrl = `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}`;

const viewports = [
  { width: 320, height: 844 },
  { width: 375, height: 812 },
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1024, height: 900 },
  { width: 1440, height: 1000 },
] as const;

async function authenticate(
  context: BrowserContext,
  accessToken: "e2e-access" | "e2e-super-admin-access",
) {
  await context.addCookies([
    {
      name: "cns_access",
      value: accessToken,
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "cns_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
    ...(accessToken === "e2e-access"
      ? [
          {
            name: "cns_e2e_persona",
            value: "applicant",
            domain: "127.0.0.1",
            path: "/",
            sameSite: "Lax" as const,
          },
        ]
      : []),
  ]);
}

async function authenticateViewer(context: BrowserContext) {
  await context.addCookies([
    {
      name: "cns_access",
      value: "e2e-access",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "cns_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
    {
      name: "cns_e2e_persona",
      value: "public",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
}

async function expectResponsivePage(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
}

test("applicant dashboard keeps one clear next action at every breakpoint", async ({
  context,
  page,
  request,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await request.post(`${mockApiUrl}/api/e2e/reset-needs-supplement`);
  await authenticate(context, "e2e-access");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/dashboard");
  await expect(
    page.getByRole("heading", { level: 1, name: "Việc cần làm" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Bổ sung tài liệu được yêu cầu" }),
  ).toHaveCount(1);

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await expectResponsivePage(page);
  }
});

test("viewer dashboard keeps public discovery as its primary action", async ({
  context,
  page,
}, testInfo) => {
  await authenticateViewer(context);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/dashboard");

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Tra cứu đề cử và chứng thư",
    }),
  ).toBeVisible();
  await expect(page.getByText("Không gian tra cứu")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Tìm kiếm đề cử" }),
  ).toHaveAttribute("href", "/search");

  const targetViewports =
    testInfo.project.name === "desktop-chrome"
      ? viewports
      : [{ width: 390, height: 844 }];
  for (const viewport of targetViewports) {
    await page.setViewportSize(viewport);
    await expectResponsivePage(page);
  }
});

test("operations dashboard prioritizes work without horizontal overflow", async ({
  context,
  page,
  request,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await request.post(`${mockApiUrl}/api/e2e/reset-operations-job`);
  await authenticate(context, "e2e-super-admin-access");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/admin/dashboard");
  const hrQueue = page.locator(
    'section[aria-labelledby="hr-dashboard-summary-title"]',
  );
  await expect(hrQueue).toBeVisible();
  await expect(hrQueue.locator('a[href="/admin/leave"]')).toContainText("3");
  await expect(hrQueue.locator('a[href="/admin/overtime"]')).toContainText("4");
  await expect(
    page
      .getByRole("main")
      .getByRole("heading", { level: 1, name: "Tổng quan vận hành" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Xem việc cần xử lý" }),
  ).toHaveCount(1);

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await expectResponsivePage(page);
  }
});

test("mobile workspace drawer exposes complete navigation and restores focus", async ({
  context,
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chrome");
  await authenticate(context, "e2e-access");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 560 });
  await page.goto("/dashboard");

  const trigger = page.getByRole("button", {
    name: "Mở điều hướng workspace",
  });
  await trigger.click();

  const drawer = page.getByRole("dialog", { name: "Điều hướng workspace" });
  await expect(drawer).toBeVisible();
  await expect(
    drawer.getByRole("link", { name: "Hồ sơ của tôi" }),
  ).toBeVisible();
  await expect(
    drawer.getByRole("link", { name: "Hoạt động gần đây" }),
  ).toBeVisible();
  await expect(
    drawer.getByRole("link", { name: "Chứng thư", exact: true }),
  ).toBeVisible();
  await expect(
    drawer.getByRole("group", { name: "Chọn giao diện" }),
  ).toBeVisible();
  await expect(drawer.getByRole("button", { name: "Đăng xuất" })).toBeVisible();
  const logoutBox = await drawer
    .getByRole("button", { name: "Đăng xuất" })
    .boundingBox();
  expect(logoutBox).not.toBeNull();
  expect(logoutBox!.y + logoutBox!.height).toBeLessThanOrEqual(
    page.viewportSize()!.height,
  );
  await page.screenshot({
    path: testInfo.outputPath("mobile-workspace-drawer.png"),
  });
  const menuText = await drawer
    .getByRole("link", { name: "Tìm đề cử" })
    .evaluate((link) => getComputedStyle(link).color);
  expect(menuText).toBe(
    await drawer.evaluate((panel) => getComputedStyle(panel).color),
  );
  await expectResponsivePage(page);

  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
  await expect(trigger).toBeFocused();
});

test("recent dossier status stays on one line on mobile", async ({
  context,
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chrome");
  await authenticate(context, "e2e-access");
  await page.route("**/api/v1/dossiers?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: [
          {
            id: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
            code: "TMI-2026-001",
            title: "Video chào mừng Tinh Hoa Việt",
            status: "CERTIFICATE_ISSUED",
          },
        ],
        meta: { page: 1, pageSize: 5, total: 1 },
      }),
    });
  });
  await page.goto("/dashboard");

  const recent = page.getByRole("heading", { name: "Hồ sơ gần đây" });
  const row = recent.locator("xpath=ancestor::section[1]").getByRole("link", {
    name: /Video chào mừng Tinh Hoa Việt/,
  });
  const badge = row.getByText("Đã phát hành chứng thư");
  await expect(badge).toBeVisible();
  const titleBox = await row
    .getByText("Video chào mừng Tinh Hoa Việt")
    .boundingBox();
  const badgeBox = await badge.boundingBox();
  expect(titleBox).not.toBeNull();
  expect(badgeBox).not.toBeNull();
  expect(badgeBox!.y).toBeGreaterThan(titleBox!.y);
  expect(badgeBox!.height).toBeLessThan(36);
  expect(badgeBox!.x + badgeBox!.width).toBeLessThanOrEqual(
    page.viewportSize()!.width,
  );
});

test("mobile workspace navigation stays compact, centered and touch friendly", async ({
  context,
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chrome");
  await authenticate(context, "e2e-access");
  await page.goto("/dashboard");

  const navigation = page.locator(".dashboard-mobile-navigation");
  await expect(navigation).toBeVisible();

  const navigationBox = await navigation.boundingBox();
  const viewportWidth = await page.evaluate(() => window.innerWidth);
  expect(navigationBox).not.toBeNull();
  expect(navigationBox!.width).toBeLessThanOrEqual(576);
  expect(
    Math.abs(navigationBox!.x - (viewportWidth - navigationBox!.width) / 2),
  ).toBeLessThanOrEqual(1);

  const controls = navigation.locator(".dashboard-mobile-navigation__link");
  await expect(
    navigation.getByRole("link", { name: "Tìm đề cử", exact: true }),
  ).toBeVisible();
  for (const control of await controls.all()) {
    const box = await control.boundingBox();
    const iconBox = await control
      .locator(".dashboard-mobile-navigation__icon")
      .boundingBox();
    expect(box).not.toBeNull();
    expect(iconBox).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(44);
    expect(box!.height).toBeGreaterThanOrEqual(56);
    expect(
      Math.abs(iconBox!.x + iconBox!.width / 2 - (box!.x + box!.width / 2)),
    ).toBeLessThanOrEqual(1);
  }

  const labelWhiteSpace = await controls
    .first()
    .locator("span")
    .last()
    .evaluate((element) => getComputedStyle(element).whiteSpace);
  expect(labelWhiteSpace).toBe("normal");

  const activeBackground = await navigation
    .locator(".dashboard-mobile-navigation__link--active")
    .evaluate((element) => getComputedStyle(element).backgroundColor);
  expect(activeBackground).not.toBe("rgb(68, 90, 54)");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
