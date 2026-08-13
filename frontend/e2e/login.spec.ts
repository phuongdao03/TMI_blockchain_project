import { expect, test } from "@playwright/test";

const password = "correct horse battery staple";

test("applicant signs in with Firebase email and securely signs out", async ({
  page,
  context,
}) => {
  await page.goto("/login?accountType=INDIVIDUAL_APPLICANT");
  await page
    .getByRole("textbox", { name: "Email" })
    .fill("applicant@tmigroup.vn");
  await page.getByLabel("Mật khẩu").fill(password);
  await page.getByRole("button", { name: "Đăng nhập" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  const cookies = await context.cookies();
  expect(cookies.find(({ name }) => name === "tmi_access")?.httpOnly).toBe(
    true,
  );
  expect(cookies.find(({ name }) => name === "tmi_refresh")?.httpOnly).toBe(
    true,
  );
  expect(cookies.find(({ name }) => name === "tmi_csrf")?.httpOnly).toBe(false);
  expect(
    await page.evaluate(() => localStorage.getItem("access_token")),
  ).toBeNull();

  const visibleText = await page.locator("body").innerText();
  expect(visibleText).not.toMatch(
    /\b(?:APPLICANT|REVIEWER|COUNCIL_MEMBER|SUPER_ADMIN)\b/,
  );
  await page.getByRole("button", { name: "Đăng xuất" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(
    (await context.cookies()).filter(({ name }) => name.startsWith("tmi_")),
  ).toHaveLength(0);
});

test("applicant signs in with Google through Firebase exchange", async ({
  page,
}) => {
  await page.goto("/login?accountType=INDIVIDUAL_APPLICANT");
  await page.getByRole("button", { name: "Tiếp tục với Google" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("email signup sends Firebase verification without exposing internal access", async ({
  page,
}) => {
  await page.goto("/register");
  await page.getByRole("radio", { name: /Cá nhân/ }).click();
  await page
    .getByRole("textbox", { name: "Email" })
    .fill("new-applicant@tmigroup.vn");
  await page.getByLabel("Mật khẩu", { exact: true }).fill(password);
  await page.getByLabel("Xác nhận mật khẩu").fill(password);
  await page.getByRole("button", { name: "Đăng ký" }).click();

  await expect(page.getByRole("status")).toContainText(
    "hướng dẫn xác minh đã được gửi",
  );
  const visibleText = await page.locator("body").innerText();
  expect(visibleText).not.toMatch(
    /\b(?:REVIEWER|COUNCIL_MEMBER|SUPER_ADMIN|database|schema)\b/i,
  );
});

test("password recovery uses Firebase one-time action code", async ({
  page,
}) => {
  await page.goto("/forgot-password");
  await page
    .getByRole("textbox", { name: "Email" })
    .fill("applicant@tmigroup.vn");
  await page.getByRole("button", { name: "Gửi hướng dẫn" }).click();
  await expect(page.getByRole("status")).toContainText(
    "đặt lại mật khẩu đã được gửi",
  );

  await page.goto("/reset-password?oobCode=e2e-valid-reset-code-123456789012");
  await page.getByLabel("Mật khẩu mới", { exact: true }).fill(password);
  await page.getByLabel("Xác nhận mật khẩu mới").fill(password);
  await page.getByRole("button", { name: "Cập nhật mật khẩu" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Mật khẩu đã được cập nhật",
  );
});

test("dashboard rotates a refresh-only session before rendering", async ({
  page,
  context,
}) => {
  await context.addCookies([
    {
      name: "tmi_refresh",
      value: "e2e-refresh",
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
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard$/);
  expect(
    (await context.cookies()).find(({ name }) => name === "tmi_access")
      ?.httpOnly,
  ).toBe(true);
});
