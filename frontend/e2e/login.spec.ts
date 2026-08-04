import { expect, test } from "@playwright/test";

test("login establishes cookie session and opens the protected dashboard", async ({
  page,
  context,
}) => {
  await page.goto("/login");

  await expect(
    page.getByRole("heading", { level: 1, name: "Đăng nhập" }),
  ).toBeVisible();
  await page.getByRole("textbox", { name: "Email" }).fill("owner@tmigroup.vn");
  await page.getByLabel("Mật khẩu").fill("correct horse battery staple");
  await page.getByRole("button", { name: "Đăng nhập" }).click();

  await expect(page).toHaveURL(/\/admin\/noi-dung$/);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  const cookies = await context.cookies();
  expect(cookies.find(({ name }) => name === "tmi_access")?.httpOnly).toBe(
    true,
  );
  expect(cookies.find(({ name }) => name === "tmi_refresh")?.httpOnly).toBe(
    true,
  );
  expect(cookies.find(({ name }) => name === "tmi_csrf")?.httpOnly).toBe(false);
  expect(
    await page.evaluate(() => window.localStorage.getItem("access_token")),
  ).toBeNull();
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
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const accessCookie = (await context.cookies()).find(
    ({ name }) => name === "tmi_access",
  );
  expect(accessCookie?.httpOnly).toBe(true);
});
