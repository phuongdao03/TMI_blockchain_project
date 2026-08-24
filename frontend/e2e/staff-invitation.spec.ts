import { expect, test } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-staff-invitations");
});

test("invited staff accepts once, enrolls TOTP and removes setup secret", async ({
  page,
}, testInfo) => {
  const tokenPrefix = `${testInfo.project.name === "mobile-chrome" ? "m" : "d"}${testInfo.repeatEachIndex}`;
  const token = `${tokenPrefix}${"a".repeat(48 - tokenPrefix.length)}`;
  await page.goto(`/staff-invitation?token=${token}`);
  await page
    .getByRole("button", { name: "Xác minh email và tiếp tục" })
    .click();

  await expect(page.getByText("E2E-TOTP-SETUP-KEY")).toBeVisible();
  await page.getByLabel("Mã xác minh 6 số").fill("654321");
  await page.getByRole("button", { name: "Kích hoạt bảo vệ hai bước" }).click();

  await expect(page).toHaveURL(/\/login\?mfa=enrolled$/);
  await expect(page.getByText("E2E-TOTP-SETUP-KEY")).toHaveCount(0);
});

test("staff completes the Firebase TOTP challenge before entering operations", async ({
  page,
}) => {
  await page.goto("/login");
  await page
    .getByRole("textbox", { name: "Email" })
    .fill("reviewer@tmigroup.vn");
  await page
    .getByLabel("Mật khẩu", { exact: true })
    .fill("correct horse battery staple");
  await page.getByRole("button", { name: "Đăng nhập" }).click();

  await expect(page.getByLabel("Mã 6 số từ ứng dụng xác thực")).toBeVisible();
  await page.getByLabel("Mã 6 số từ ứng dụng xác thực").fill("654321");
  await page.getByRole("button", { name: "Xác nhận mã" }).click();
  await expect(page).toHaveURL(/\/reviews$/);
});
