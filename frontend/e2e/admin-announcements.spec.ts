import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context }) => {
  await context.addCookies([
    {
      name: "cns_access",
      value: "e2e-super-admin-access",
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
  ]);
});

test("admin can preview and send to one active account", async ({ page }) => {
  await page.goto("/admin/notifications");
  await expect(
    page
      .locator("#main-content")
      .getByRole("heading", { name: "Gửi thông báo" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Một người/ }).click();
  await page.getByLabel("Tìm tài khoản").fill("Nguyễn");
  await page.getByRole("button", { name: "Tìm", exact: true }).click();
  await page.getByRole("button", { name: /Nguyễn Văn An/ }).click();
  await page.getByLabel("Tiêu đề").fill("Lịch làm việc mới");
  await page
    .getByLabel("Nội dung")
    .fill("Vui lòng kiểm tra lịch làm việc tuần tới.");
  await page.getByRole("button", { name: "Xem số người nhận" }).click();
  await expect(page.getByText("1 tài khoản sẽ nhận thông báo.")).toBeVisible();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Gửi thông báo" }).click();
  await expect(page.getByText("Đã gửi cho 1 tài khoản.")).toBeVisible();
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
});
