import { expect, test } from "@playwright/test";

test("mobile home shows imagery and account actions without opening the menu", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chrome");
  await page.goto("/");

  const story = page.locator(".registry-heritage");
  await expect(story).toBeVisible();
  await expect(story.locator("img")).toHaveCount(3);
  const logo = story.locator(".registry-heritage__logo");
  const bird = story.locator(".registry-heritage__bird");
  expect((await logo.boundingBox())!.width).toBeGreaterThan(
    (await bird.boundingBox())!.width,
  );
  await expect(story.locator(".registry-heritage__light")).toHaveCSS(
    "animation-name",
    "heritage-light-pass",
  );
  await expect(logo).toHaveCSS("animation-name", "heritage-seal-breathe");
  await expect
    .poll(() =>
      story
        .locator("img")
        .evaluateAll((images) =>
          images.every((image) => (image as HTMLImageElement).naturalWidth > 0),
        ),
    )
    .toBe(true);

  const actions = page.getByRole("navigation", { name: "Truy cập tài khoản" });
  const login = actions.getByRole("link", { name: "Đăng nhập" });
  const register = actions.getByRole("link", { name: "Đăng ký" });
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

test("public header keeps a stable desktop navigation when viewport width changes", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await page.goto("/");

  const header = page.locator(".public-header");
  const artwork = page.locator(".registry-heritage");
  await expect(artwork).toBeVisible();
  await expect(artwork.locator("img")).toHaveCount(3);
  const navigation = page.getByRole("navigation", { name: "Điều hướng chính" });
  const brand = header.locator(".brand-mark");

  for (const width of [1024, 1280, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(navigation).toBeVisible();
    const brandBox = await brand.boundingBox();
    const navigationBox = await navigation.boundingBox();
    expect(brandBox).not.toBeNull();
    expect(navigationBox).not.toBeNull();
    expect(navigationBox!.y).toBeGreaterThanOrEqual(
      brandBox!.y + brandBox!.height,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }

  await page.setViewportSize({ width: 1000, height: 900 });
  await expect(navigation).toBeHidden();
  await expect(page.getByRole("button", { name: "Mở menu" })).toBeVisible();
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

test("medium desktop shell keeps direct navigation and workspace access", async ({
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
  await expect(
    page.getByRole("navigation", { name: "Điều hướng chính" }),
  ).toBeVisible();
  await expect(page.locator(".public-header__menu")).toBeHidden();
});
