import { expect, test } from "@playwright/test";

test("mobile home shows account actions without opening the menu", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chrome");
  await page.goto("/");

  const actions = page.getByRole("navigation", { name: "Truy cập tài khoản" });
  const login = actions.getByRole("link", { name: "Đăng nhập" });
  const register = actions.getByRole("link", { name: "Tạo tài khoản" });
  await expect(login).toBeVisible();
  await expect(register).toBeVisible();
  for (const action of [login, register]) {
    const box = await action.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(44);
    expect(box!.y + box!.height).toBeLessThan(page.viewportSize()!.height);
  }
  await page.screenshot({
    path: testInfo.outputPath("mobile-home-actions.png"),
  });
});

test("mobile home loads featured works when they approach the viewport", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chrome");
  const featuredRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/public/works?")) {
      featuredRequests.push(request.url());
    }
  });

  await page.goto("/");
  await page.waitForLoadState("networkidle");
  expect(featuredRequests).toHaveLength(0);

  await page.locator(".home-featured").scrollIntoViewIfNeeded();
  await expect.poll(() => featuredRequests.length).toBe(1);
});

test("compact public shell keeps the account entry in its drawer and uses a full-height page frame", async ({
  context,
  page,
}, testInfo) => {
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
      name: "cns_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
    {
      name: "cns_e2e_persona",
      value: "public",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);

  await page.setViewportSize({ width: 540, height: 640 });
  await page.goto("/verify");

  const header = page.locator(".public-header");
  const quickNavigation = page.getByRole("navigation", {
    name: "Điều hướng nhanh",
  });
  const menuButton = page.getByRole("button", { name: "Mở menu" });

  await expect(header).toBeVisible();
  await expect(quickNavigation).toBeVisible();
  await expect(
    quickNavigation.getByRole("link", { name: "Không gian của tôi" }),
  ).toBeVisible();
  await expect(menuButton).toBeVisible();
  await expect
    .poll(() =>
      header.evaluate(
        (element) => element.scrollWidth <= element.clientWidth + 1,
      ),
    )
    .toBe(true);

  await menuButton.click();
  await expect(
    page
      .locator(".public-mobile-nav")
      .getByRole("link", { name: "Không gian của tôi" }),
  ).toBeVisible();

  await expect(page.locator(".public-shell")).toHaveCSS("display", "flex");
});

test("signed-in mobile visitor keeps quick navigation across discovery pages", async ({
  context,
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chrome");
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
      name: "cns_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
    {
      name: "cns_e2e_persona",
      value: "public",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);

  await page.goto("/dashboard");
  await page
    .getByRole("navigation", { name: "Điều hướng nhanh" })
    .getByRole("link", { name: "Tìm đề cử" })
    .click();

  const quickNavigation = page.getByRole("navigation", {
    name: "Điều hướng nhanh",
  });
  await expect(
    quickNavigation.getByRole("link", { name: "Tìm đề cử" }),
  ).toHaveAttribute("aria-current", "page");
  await quickNavigation.getByRole("link", { name: "Thư viện đề cử" }).click();
  await expect(
    quickNavigation.getByRole("link", { name: "Thư viện đề cử" }),
  ).toHaveAttribute("aria-current", "page");
  await expect(page.locator(".public-workspace-return")).toBeHidden();
  await expect(
    quickNavigation.getByRole("link", { name: "Không gian của tôi" }),
  ).toBeVisible();
});

test("medium public shell keeps a one-tap return to the workspace", async ({
  context,
  page,
}, testInfo) => {
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
      name: "cns_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
    {
      name: "cns_e2e_persona",
      value: "public",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);

  await page.setViewportSize({ width: 1145, height: 800 });
  await page.goto("/verify");

  await expect(page.locator(".public-header__workspace")).toBeVisible();
  await expect(page.locator(".public-header__menu")).toBeVisible();
});
