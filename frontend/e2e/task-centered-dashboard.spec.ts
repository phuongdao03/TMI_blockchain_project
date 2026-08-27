import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { BrowserContext, Page } from "@playwright/test";

const viewports = [
  { width: 320, height: 844 },
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
      name: "tmi_access",
      value: accessToken,
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "tmi_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
    ...(accessToken === "e2e-access"
      ? [
          {
            name: "tmi_e2e_persona",
            value: "applicant",
            domain: "127.0.0.1",
            path: "/",
            sameSite: "Lax" as const,
          },
        ]
      : []),
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
  await request.post("http://127.0.0.1:4010/api/e2e/reset-needs-supplement");
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

test("operations dashboard prioritizes work without horizontal overflow", async ({
  context,
  page,
  request,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await request.post("http://127.0.0.1:4010/api/e2e/reset-operations-job");
  await authenticate(context, "e2e-super-admin-access");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/admin/dashboard");
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
  await expectResponsivePage(page);

  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
  await expect(trigger).toBeFocused();
});
