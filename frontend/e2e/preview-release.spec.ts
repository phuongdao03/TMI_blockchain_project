import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("preview public home keeps submission closed and hides internal language", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Suy tôn trí tuệ. Lưu truyền di sản.",
    }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("navigation", { name: "Điều hướng chính" })
      .getByRole("link", { name: "Khám phá đề cử", exact: true }),
  ).toHaveAttribute("href", "/works");
  await expect(
    page.getByRole("button", { name: "Bắt đầu hồ sơ đề cử" }),
  ).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Tạo hồ sơ mới" })).toHaveCount(
    0,
  );
  await expect(page.locator('a[href="/dossiers/new"]')).toHaveCount(0);

  const text = await page.locator("body").innerText();
  expect(text).not.toMatch(
    /Authentication is required|ADMIN|REVIEWER|COUNCIL|database|backend|API|endpoint|loại tài khoản/i,
  );

  for (const viewport of [
    { width: 320, height: 844 },
    { width: 1440, height: 1000 },
  ]) {
    await page.setViewportSize(viewport);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  }
});

test("public discovery keeps account navigation available to signed in users", async ({
  context,
  page,
}, testInfo) => {
  test.setTimeout(90_000);
  test.skip(testInfo.project.name !== "desktop-chrome");
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
      name: "cns_e2e_persona",
      value: "applicant",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/dashboard");
  const dashboardNavigation = page.getByRole("navigation", {
    name: "Điều hướng",
  });
  await dashboardNavigation
    .getByRole("link", { name: "Thư viện đề cử" })
    .click();
  await expect(page).toHaveURL(/\/works$/, { timeout: 30_000 });
  const accountMenu = page.locator(".public-user-menu");
  await accountMenu.locator("summary").click();
  const accountNavigation = page.getByRole("navigation", {
    name: "Menu tài khoản",
  });
  await expect(accountNavigation).toBeVisible();
  await expect(
    accountNavigation.getByRole("link", { name: "Không gian cá nhân" }),
  ).toHaveAttribute("href", "/workspace");
  await expect(
    page.getByRole("heading", { name: "Thư viện đề cử" }),
  ).toBeVisible();
  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("workspace-library-desktop.png"),
  });

  await page.goto("/works");
  await expect(page).toHaveURL(/\/works$/, { timeout: 30_000 });
  await expect(
    page.getByRole("heading", { name: "Thư viện đề cử" }),
  ).toBeVisible();

  await page.setViewportSize({ width: 320, height: 844 });
  await page.goto("/verify");
  await expect(page.getByRole("button", { name: "Mở menu" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Kiểm tra bằng xác lập" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("workspace-verify-mobile.png"),
  });
});
