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

test("admin users remains operable on desktop and mobile", async ({ page }) => {
  const userId = "b57912cc-714c-4ab5-9fd9-1c5b38cd902b";
  const envelope = (data: unknown) => ({
    success: true,
    data,
    meta: {
      request_id: "admin-users-fixture",
      page: 1,
      pageSize: 20,
      total: 0,
    },
  });
  await page.route(`**/api/v1/admin/users/${userId}`, (route) =>
    route.fulfill({
      json: envelope({
        id: userId,
        email: "an@example.com",
        fullName: "Nguyễn Văn An",
        status: "ACTIVE",
        isTestAccount: false,
        isEmailVerified: true,
        providers: ["GOOGLE"],
        roles: ["USER"],
        createdAt: "2026-08-20T09:00:00Z",
        lastLoginAt: "2026-08-29T09:00:00Z",
        disabledAt: null,
        deletedAt: null,
      }),
    }),
  );
  await page.route("**/api/v1/admin/audit?**", (route) =>
    route.fulfill({ json: envelope([]) }),
  );
  await page.route(
    "**/api/v1/admin/test-applicant-invitations",
    async (route) => {
      expect(route.request().postDataJSON()).toEqual({
        email: "tester@example.com",
      });
      await route.fulfill({
        status: 201,
        json: envelope({
          id: "test-invitation-1",
          email: "tester@example.com",
          role: "USER",
          status: "PENDING",
        }),
      });
    },
  );
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

  await page.getByLabel("Email tài khoản TEST mới").fill("tester@example.com");
  await page.getByRole("button", { name: "Gửi lời mời TEST" }).click();
  await expect(
    page.getByText(/Đã gửi lời mời TEST đến tester@example.com/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Xem chi tiết" }).first().click();
  await expect(
    page.getByRole("dialog", { name: "Chi tiết tài khoản" }),
  ).toBeVisible();
  await expect(page.getByText("Tài khoản thật")).toBeVisible();
  await expect(page.getByText(/không thể chuyển sang TEST/)).toBeVisible();
  await page.getByRole("button", { name: "Đóng chi tiết" }).click();

  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
});
