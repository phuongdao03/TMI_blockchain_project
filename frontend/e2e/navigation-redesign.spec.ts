import { expect, test, type BrowserContext, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { selectWorkspaceTheme } from "./workspace-theme";

async function session(context: BrowserContext, persona: string) {
  await context.clearCookies();
  await context.addCookies(
    [
      ["cns_access", "e2e-access"],
      ["cns_refresh", "e2e-refresh"],
      ["cns_csrf", "e2e-csrf"],
      ["cns_e2e_persona", persona],
    ].map(([name, value]) => ({
      name: name!,
      value: value!,
      domain: "127.0.0.1",
      path: "/",
    })),
  );
}
async function fits(page: Page) {
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(page.viewportSize()!.width);
  const bar = page.locator(".site-mobile-navigation");
  if (await bar.isVisible()) {
    expect(
      await bar.locator('[aria-current="page"]').count(),
    ).toBeLessThanOrEqual(1);
    expect(await bar.getByRole("button").count()).toBe(0);
    for (const link of await bar.getByRole("link").all()) {
      const box = await link.boundingBox();
      expect(box!.width).toBeGreaterThanOrEqual(44);
      expect(box!.height).toBeGreaterThanOrEqual(44);
      expect(
        await link
          .locator("span")
          .evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
      ).toBe(true);
    }
  }
}

test("desktop navigation omits the redundant About menu", async ({
  page,
}, info) => {
  test.skip(info.project.name !== "desktop-chrome");
  await page.goto("/");
  await expect(page.locator(".public-about-menu")).toHaveCount(0);
});

test("search overlay respects both themes at phone and desktop widths", async ({
  page,
}, info) => {
  test.skip(info.project.name !== "desktop-chrome");
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/verify");
  for (const theme of ["Giao diện sáng", "Giao diện tối"]) {
    await page
      .getByRole("button", { name: theme, exact: true })
      .first()
      .click();
    for (const width of [320, 390, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      const trigger = page.getByRole("button", { name: "Mở tìm kiếm" });
      await trigger.click();
      const dialog = page.getByRole("dialog", { name: "Tìm kiếm đề cử" });
      await expect(dialog.getByRole("combobox")).toBeFocused();
      const box = await dialog.boundingBox();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width);
      const scan = await new AxeBuilder({ page })
        .include("#navigation-search")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze();
      expect(scan.violations).toEqual([]);
      await page.screenshot({
        path: info.outputPath(`search-${theme}-${width}.png`),
        animations: "disabled",
      });
      await page.keyboard.press("Escape");
      await expect(trigger).toBeFocused();
    }
  }
});

test("navigation fits nine widths in two themes with working grouped drawers", async ({
  page,
}, info) => {
  test.skip(info.project.name !== "desktop-chrome");
  test.setTimeout(240_000);
  await page.goto("/");
  for (const theme of ["Giao diện sáng", "Giao diện tối"]) {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page
      .getByRole("button", { name: theme, exact: true })
      .first()
      .click();
    for (const width of [320, 360, 375, 390, 414, 430, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await fits(page);
      if (width < 1024) {
        const bar = page.getByRole("navigation", {
          name: "Điều hướng di động",
        });
        await expect(bar.getByRole("link")).toHaveCount(5);
        await page
          .getByRole("button", { name: "Mở menu", exact: true })
          .click();
        const drawer = page.getByRole("dialog", { name: "Menu công khai" });
        await expect(drawer).toBeVisible();
        await expect(
          drawer.getByRole("group", { name: "Tham gia", exact: true }),
        ).toBeVisible();
        await expect(
          drawer.getByRole("link", { name: "Thư viện ảnh", exact: true }),
        ).toHaveCount(0);
        expect(await page.evaluate(() => document.body.style.overflow)).toBe(
          "hidden",
        );
        if (width === 390)
          await page.screenshot({
            animations: "disabled",
            path: info.outputPath(`drawer-${theme}-${width}.png`),
          });
        await page.keyboard.press("Escape");
        await expect(drawer).toHaveCount(0);
        await expect(
          page.getByRole("button", { name: "Mở menu", exact: true }),
        ).toBeFocused();
        expect(
          await page.evaluate(() => document.body.style.overflow),
        ).not.toBe("hidden");
      }
      if (width === 390 || width === 1440)
        await page.screenshot({
          animations: "disabled",
          path: info.outputPath(`header-${theme}-${width}.png`),
        });
    }
  }
});

test("anchors, back, forward, focus trap and search stay usable on mobile", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/works");
  const trigger = page.getByRole("button", { name: "Mở menu", exact: true });
  await trigger.click();
  const drawer = page.getByRole("dialog", { name: "Menu công khai" });
  const close = drawer.getByRole("button", { name: "Đóng menu", exact: true });
  await expect(close).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(
    drawer.getByRole("link", { name: "Đăng ký", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  await page.keyboard.press("Escape");
  await page
    .getByRole("navigation", { name: "Điều hướng di động" })
    .getByRole("link", { name: "Trang chủ", exact: true })
    .click();
  await expect(drawer).toHaveCount(0);
  await page
    .getByRole("link", { name: "Xem văn bản thành lập", exact: true })
    .click();
  await expect(page).toHaveURL(/#van-ban-thanh-lap$/);
  await expect(page.locator("#van-ban-thanh-lap")).toBeInViewport();
  await trigger.click();
  await page.goBack();
  await expect(drawer).toHaveCount(0);
  await page.goForward();
  await expect(page).toHaveURL(/#van-ban-thanh-lap$/);
  await page.getByRole("button", { name: "Mở tìm kiếm" }).click();
  const search = page.getByRole("dialog", { name: "Tìm kiếm đề cử" });
  const input = search.getByRole("combobox");
  await expect(input).toBeFocused();
  await input.fill("văn hóa");
  await search.getByRole("button", { name: "Xóa nội dung tìm kiếm" }).click();
  await expect(input).toHaveValue("");
  await expect(input).toBeFocused();
  await input.fill("văn hóa");
  await input.press("Enter");
  await expect(page).toHaveURL(/\/works\?query=/);
  await expect(search).toHaveCount(0);
  await page.getByRole("button", { name: "Mở tìm kiếm" }).click();
  await expect(
    search.getByRole("link", { name: "Bạn cần tra cứu bằng xác lập?" }),
  ).toHaveAttribute("href", "/verify");
  await page.screenshot({
    animations: "disabled",
    path: info.outputPath("search-mobile.png"),
  });
  const scan = await new AxeBuilder({ page })
    .include("#navigation-search")
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(scan.violations).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Mở tìm kiếm" })).toBeFocused();
  await trigger.click();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(drawer).toHaveCount(0);
});

test("workspaces preserve applicant reviewer and administrator entry points", async ({
  page,
  context,
}, info) => {
  test.setTimeout(240_000);
  test.skip(info.project.name !== "desktop-chrome");
  for (const [persona, path, label] of [
    ["applicant", "/workspace", "Điều hướng di động"],
    ["reviewer", "/reviews", "Điều hướng công việc"],
    ["super-admin", "/admin", ""],
  ] as const) {
    await session(context, persona);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(path);
    if (label)
      await expect(page.getByRole("navigation", { name: label })).toBeVisible();
    if (persona === "reviewer") {
      const bar = page.getByRole("navigation", { name: label });
      await expect(
        bar.getByRole("link", { name: "Thẩm định", exact: true }),
      ).toHaveAttribute("aria-current", "page");
      await expect(
        bar.getByRole("link", { name: "Công việc", exact: true }),
      ).toHaveAttribute("href", "/work-allocations");
      await expect(
        bar.getByRole("link", { name: "Gửi hồ sơ", exact: true }),
      ).toHaveCount(0);
    }
    for (const theme of ["Giao diện sáng", "Giao diện tối"] as const) {
      await page.setViewportSize({ width: 1440, height: 900 });
      await selectWorkspaceTheme(page, theme);
      for (const width of [320, 360, 375, 390, 414, 430, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await fits(page);
      }
      await page.setViewportSize({ width: 390, height: 844 });
      await page
        .getByRole("button", {
          name:
            persona === "super-admin"
              ? "Mở điều hướng quản trị"
              : "Mở điều hướng workspace",
        })
        .click();
      const drawer = page.getByRole("dialog");
      await expect(drawer).toBeVisible();
      if (persona === "super-admin") {
        const group = drawer.getByRole("button", {
          name: "Nhân sự",
          exact: true,
        });
        if ((await group.getAttribute("aria-expanded")) === "true")
          await group.click();
        await expect(group).toHaveAttribute("aria-expanded", "false");
        await page.keyboard.press("Escape");
        await page
          .getByRole("button", { name: "Mở điều hướng quản trị" })
          .click();
        await expect(
          drawer.getByRole("button", { name: "Nhân sự", exact: true }),
        ).toHaveAttribute("aria-expanded", "false");
      }
      await page.screenshot({
        animations: "disabled",
        path: info.outputPath(`${persona}-${theme}-drawer.png`),
      });
      await page.keyboard.press("Escape");
    }
  }
});
