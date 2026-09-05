import { expect, test } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-staff-invitations");
});

test("invited staff verifies email and activates the account once", async ({
  page,
}, testInfo) => {
  const device = testInfo.project.name === "mobile-chrome" ? "m" : "d";
  const tokenPrefix = `${device}${testInfo.repeatEachIndex}`;
  const token = `${tokenPrefix}${"a".repeat(48 - tokenPrefix.length)}`;

  await page.goto(`/staff-invitation?token=${token}`);
  await expect(page.getByRole("button", { name: "Theo thiết bị" })).toBeEnabled(
    {
      timeout: 45_000,
    },
  );
  await page
    .getByRole("button", { name: "Xác minh email và kích hoạt tài khoản" })
    .click();

  await expect(page).toHaveURL(/\/login\?invitation=accepted$/);
});

test("reviewer signs in directly after Firebase authentication", async ({
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

  await expect(page).toHaveURL(/\/reviews$/);
});
