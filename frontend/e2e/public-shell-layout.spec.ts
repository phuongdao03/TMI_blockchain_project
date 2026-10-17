import { expect, test } from "@playwright/test";

test("mobile home shows the brand logo and account actions without opening the menu", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chrome");
  await page.goto("/");

  const story = page.locator(".registry-heritage");
  await expect(story).toBeVisible();
  const logo = story.locator(".registry-heritage__logo");
  await expect(story.locator("img")).toHaveCount(1);
  await expect(logo).toBeVisible();
  await expect(
    story.locator(
      ".registry-heritage__bird, .registry-heritage__drum, .registry-heritage__seal",
    ),
  ).toHaveCount(0);
  await expect(story).toHaveCSS("border-top-width", "0px");
  await expect(story).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  await expect(story).toHaveCSS("overflow", "visible");
  await expect
    .poll(() =>
      logo.evaluate((image) => (image as HTMLImageElement).naturalWidth > 0),
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

test("heritage logo fits without covering actions across mobile and tablet widths", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const heroLocator = page.locator(".registry-hero");
  await expect(heroLocator).toBeVisible();

  for (const width of [320, 390, 640, 736, 768]) {
    await page.setViewportSize({ width, height: 1024 });
    await expect(heroLocator).toBeVisible();
    const hero = await heroLocator.boundingBox();
    const figure = await page.locator(".registry-heritage").boundingBox();
    const logo = await page.locator(".registry-heritage__logo").boundingBox();
    const actions = await page.locator(".registry-hero__actions").boundingBox();
    expect(hero).not.toBeNull();
    expect(figure).not.toBeNull();
    expect(logo, `${width}px logo is visible`).not.toBeNull();
    expect(actions).not.toBeNull();

    expect(
      logo!.x,
      `${width}px logo is cut on the left`,
    ).toBeGreaterThanOrEqual(figure!.x - 1);
    expect(
      logo!.x + logo!.width,
      `${width}px logo is cut on the right`,
    ).toBeLessThanOrEqual(figure!.x + figure!.width + 1);
    expect(logo!.y, `${width}px logo is cut at the top`).toBeGreaterThanOrEqual(
      figure!.y - 1,
    );
    expect(
      logo!.y + logo!.height,
      `${width}px logo is cut at the bottom`,
    ).toBeLessThanOrEqual(figure!.y + figure!.height + 1);

    const overlapsActions =
      logo!.x < actions!.x + actions!.width &&
      logo!.x + logo!.width > actions!.x &&
      logo!.y < actions!.y + actions!.height &&
      logo!.y + logo!.height > actions!.y;
    expect(overlapsActions, `${width}px logo overlaps account actions`).toBe(
      false,
    );
    expect(
      logo!.y + logo!.height,
      `${width}px logo escapes the introduction`,
    ).toBeLessThanOrEqual(hero!.y + hero!.height);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
  }
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
  await expect(artwork.locator("img")).toHaveCount(1);
  await expect(artwork.locator(".registry-heritage__logo")).toBeVisible();
  await expect(
    artwork.locator(".registry-heritage__bird, .registry-heritage__drum"),
  ).toHaveCount(0);
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
  const mobileNavigation = page.getByRole("navigation", {
    name: "Điều hướng di động",
  });
  const menuButton = page.getByRole("button", { name: "Mở menu" });

  await expect(header).toBeVisible();
  await expect(mobileNavigation).toBeVisible();
  await expect(
    mobileNavigation.getByRole("link", { name: "Cá nhân", exact: true }),
  ).toHaveAttribute("href", "/workspace");
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
    page.getByRole("navigation", { name: "Menu công khai" }).getByRole("link", {
      name: "Không gian cá nhân",
    }),
  ).toBeVisible();

  await expect(page.locator(".public-shell")).toHaveCSS("display", "flex");
});

test("signed-in mobile visitor keeps primary navigation across discovery pages", async ({
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
  const mobileNavigation = page.getByRole("navigation", {
    name: "Điều hướng di động",
  });
  await mobileNavigation
    .getByRole("link", { name: "Đề cử", exact: true })
    .click();
  await expect(page).toHaveURL(/\/works$/);

  await expect(
    mobileNavigation.getByRole("link", { name: "Đề cử", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    mobileNavigation.getByRole("link", { name: "Cá nhân", exact: true }),
  ).toHaveAttribute("href", "/workspace");
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

  const accountMenu = page.locator(".public-user-menu");
  await expect(accountMenu).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Điều hướng chính" }),
  ).toBeVisible();
  await accountMenu.locator("summary").click();
  await expect(
    page
      .getByRole("navigation", { name: "Menu tài khoản" })
      .getByRole("link", { name: "Không gian cá nhân" }),
  ).toHaveAttribute("href", "/workspace");
  await expect(page.locator(".public-header__menu")).toBeHidden();
});
