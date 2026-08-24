import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("preview dashboard keeps submission closed and hides internal language", async ({
  context,
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await context.addCookies([
    {
      name: "tmi_access",
      value: "e2e-access",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "tmi_e2e_persona",
      value: "applicant",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);

  await page.goto("/dashboard");

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Khám phá những đề cử đang được giới thiệu",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Cổng gửi đề cử đang được chuẩn bị" }),
  ).toBeVisible();
  await expect(page.getByText("Sắp ra mắt", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Tìm hiểu cách tham gia" }),
  ).toHaveAttribute("href", "/coming-soon/submission");
  await expect(
    page.getByRole("button", { name: "Gửi tác phẩm hoặc hồ sơ" }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Cá nhân")).toHaveCount(0);

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

test("discovery keeps an authenticated return path across public screens", async ({
  context,
  page,
}, testInfo) => {
  test.setTimeout(90_000);
  test.skip(testInfo.project.name !== "desktop-chrome");
  await context.addCookies([
    {
      name: "tmi_access",
      value: "e2e-access",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "tmi_e2e_persona",
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
  await dashboardNavigation.getByRole("link", { name: "Tìm đề cử" }).click();
  await expect(page).toHaveURL(/\/search$/, { timeout: 30_000 });
  const publicNavigation = page.getByRole("navigation", {
    name: "Điều hướng chính",
  });
  await expect(publicNavigation).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Hồ sơ của tôi" }),
  ).toHaveAttribute("href", "/dossiers");
  await expect(
    page.getByRole("heading", { name: "Tìm nội dung bạn quan tâm" }),
  ).toBeVisible();
  await expect(
    page.getByText("Tìm kiếm đề cử", { exact: true }).last(),
  ).toBeVisible();
  await expect(page.getByText("Quay lại thư viện")).toHaveCount(0);
  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("workspace-search-desktop.png"),
  });

  await publicNavigation.getByRole("link", { name: "Đề cử" }).click();
  await expect(page).toHaveURL(/\/works$/, { timeout: 30_000 });
  await expect(publicNavigation).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Thư viện đề cử" }),
  ).toBeVisible();

  await page.setViewportSize({ width: 320, height: 844 });
  await page.goto("/verify");
  await expect(page.getByRole("button", { name: "Mở menu" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Kiểm tra chứng thư" }),
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
