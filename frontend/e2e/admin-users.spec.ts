import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context }) => {
  await context.addCookies([
    {
      name: "tmi_access",
      value: "e2e-super-admin-access",
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
  ]);
});

test("admin users remains operable on desktop and mobile", async ({ page }) => {
  await page.goto("/admin/users");

  await expect(page.getByRole("heading", { name: "Người dùng" })).toBeVisible();

  const mobile = (page.viewportSize()?.width ?? 1024) < 768;
  if (mobile) {
    await expect(page.getByTestId("admin-users-mobile")).toBeVisible();
    await expect(page.getByTestId("admin-users-table")).toBeHidden();
    await expect(
      page.getByTestId("admin-users-mobile").getByText("Nguyễn Văn An"),
    ).toBeVisible();
  } else {
    await expect(page.getByTestId("admin-users-mobile")).toBeHidden();
    await expect(page.getByTestId("admin-users-table")).toBeVisible();
    await expect(
      page.getByTestId("admin-users-table").getByText("Nguyễn Văn An"),
    ).toBeVisible();
  }

  await page.getByRole("button", { name: "Tạm đình chỉ" }).first().click();
  const confirm = page.getByRole("button", { name: "Xác nhận đình chỉ" });
  await expect(confirm).toBeDisabled();
  await page
    .getByLabel("Lý do thay đổi trạng thái")
    .fill("Phát hiện đăng nhập bất thường");
  await confirm.click();
  await expect(page.getByText(/Đã đình chỉ tài khoản/)).toBeVisible();

  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
});
