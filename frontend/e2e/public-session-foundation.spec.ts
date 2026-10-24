import { expect, test, type BrowserContext, type Page } from "@playwright/test";

async function seedSession(context: BrowserContext, refreshOnly = false) {
  await context.addCookies(
    [
      ...(refreshOnly ? [] : [["cns_access", "e2e-access", true] as const]),
      ["cns_refresh", "e2e-refresh", true] as const,
      ["cns_csrf", "e2e-csrf", false] as const,
      ["cns_e2e_persona", "applicant", false] as const,
    ].map(([name, value, httpOnly]) => ({
      name,
      value,
      httpOnly,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax" as const,
    })),
  );
}

async function expectAccount(page: Page) {
  const accountMenu = page.getByLabel("Mở menu tài khoản");
  if (await accountMenu.isVisible()) {
    await expect(accountMenu).toBeVisible();
  } else {
    const mobileMenu = page.getByRole("navigation", { name: "Menu công khai" });
    if (!(await mobileMenu.isVisible())) {
      await page.getByRole("button", { name: "Mở menu", exact: true }).click();
    }
    await expect(
      mobileMenu.getByRole("link", { name: "Không gian cá nhân" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Đóng menu", exact: true }).click();
  }
  await expect(
    page.getByRole("link", { name: "Đăng nhập", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Đăng ký", exact: true }),
  ).toHaveCount(0);
}

async function logout(page: Page) {
  const accountMenu = page.getByLabel("Mở menu tài khoản");
  if (await accountMenu.isVisible()) {
    await accountMenu.click();
  } else {
    const mobileMenu = page.getByRole("navigation", { name: "Menu công khai" });
    if (!(await mobileMenu.isVisible())) {
      await page.getByRole("button", { name: "Mở menu", exact: true }).click();
    }
  }
  await page.getByRole("button", { name: "Đăng xuất", exact: true }).click();
}

async function expectGuestAfterLogout(page: Page) {
  const loginLink = page
    .getByRole("banner")
    .getByRole("link", { name: "Đăng nhập", exact: true });
  if (await loginLink.isVisible()) {
    await expect(loginLink).toBeVisible();
  } else {
    const mobileMenu = page.getByRole("navigation", { name: "Menu công khai" });
    if (!(await mobileMenu.isVisible())) {
      await page.getByRole("button", { name: "Mở menu", exact: true }).click();
    }
    await expect(
      mobileMenu.getByRole("link", { name: "Đăng nhập", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Đóng menu", exact: true }).click();
  }
  await expect(page.getByLabel("Mở menu tài khoản")).toHaveCount(0);
}

test("guest account actions resolve at every requested viewport", async ({
  page,
}) => {
  await page.goto("/");
  for (const width of [360, 375, 390, 430, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const actions = page;
    await expect(
      actions.getByRole("link", { name: "Đăng nhập", exact: true }).first(),
    ).toBeVisible();
    await expect(
      actions.getByRole("link", { name: "Đăng ký", exact: true }).first(),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
});

test("public account survives reload and returns to guest after logout", async ({
  page,
  context,
}) => {
  await seedSession(context);
  await page.goto("/");
  await expectAccount(page);
  await page.reload();
  await expectAccount(page);
  await logout(page);
  await expectGuestAfterLogout(page);
});

test("public home recovers a refresh-only session", async ({
  page,
  context,
}) => {
  await seedSession(context, true);
  await page.goto("/");
  await expectAccount(page);
});

test("logout updates another already-open public tab", async ({
  page,
  context,
}) => {
  await seedSession(context);
  await page.goto("/");
  await expectAccount(page);
  const other = await context.newPage();
  try {
    await other.goto("/");
    await expectAccount(other);
    await logout(other);
    await expectGuestAfterLogout(page);
    await expect(page.getByRole("banner")).toBeVisible();
  } finally {
    await other.close();
  }
});
