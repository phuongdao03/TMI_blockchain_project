import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("inline reading and compact home sections work across widths and themes", async ({
  page,
}, info) => {
  test.skip(info.project.name !== "desktop-chrome");
  test.setTimeout(180_000);
  await page.goto("/");
  await expect(page.locator(".registry-kicker")).toHaveCount(0);
  await expect(page.locator(".public-about-menu")).toHaveCount(0);
  await page.locator(".proposal-inline").scrollIntoViewIfNeeded();
  const reader = page.getByRole("region", {
    name: "Trình xem proposal",
    exact: true,
  });
  await expect(reader).toBeVisible();
  const image = reader.getByRole("img");
  await expect
    .poll(() => image.evaluate((el) => (el as HTMLImageElement).naturalWidth))
    .toBeGreaterThan(0);
  await reader.getByRole("button", { name: "Trang sau", exact: true }).click();
  await expect(reader.getByRole("status")).toContainText("Trang 2 / 53");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  for (const theme of ["Giao diện sáng", "Giao diện tối"]) {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page
      .getByRole("button", { name: theme, exact: true })
      .first()
      .click();
    for (const width of [320, 360, 375, 390, 414, 430, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      for (const [name, selector] of [
        ["gallery", "#thu-vien-anh"],
        ["proposal", "#ho-so-2026"],
        ["community", ".home-community"],
      ] as const) {
        await page.locator(selector).scrollIntoViewIfNeeded();
        expect(
          await page.evaluate(() => document.documentElement.scrollWidth),
        ).toBeLessThanOrEqual(width);
        if (width === 390 || width === 1440) {
          await page.screenshot({
            path: info.outputPath(`${name}-${theme}-${width}.png`),
            animations: "disabled",
          });
          const scan = await new AxeBuilder({ page })
            .include(selector)
            .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
            .analyze();
          expect(scan.violations).toEqual([]);
        }
      }
      if (width < 768) {
        const next = page.getByRole("button", {
          name: "Ảnh tiếp theo",
          exact: true,
        });
        const box = await next.boundingBox();
        expect(box!.width).toBe(44);
        expect(box!.height).toBe(44);
        await expect(page.getByLabel("Chọn bộ ảnh")).toBeVisible();
        const thumbs = page.locator(".heritage-gallery__thumbnails");
        expect((await thumbs.boundingBox())!.height).toBeLessThanOrEqual(150);
        expect(
          (await thumbs.getByRole("button").first().boundingBox())!.width,
        ).toBeGreaterThanOrEqual(44);
      }
    }
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator("#thu-vien-anh").scrollIntoViewIfNeeded();
  await page.getByLabel("Chọn bộ ảnh").selectOption("Văn hóa & đời sống");
  await expect(page.locator(".heritage-gallery__counter")).toContainText("08");
  await page
    .getByRole("button", { name: "Xem toàn màn hình", exact: true })
    .click();
  const gallery = page.getByRole("dialog", { name: "Ảnh Tinh Hoa Việt" });
  await expect(gallery).toBeVisible();
  await gallery
    .getByRole("button", { name: "Ảnh tiếp theo trong bộ sưu tập" })
    .click();
  await expect(gallery.getByRole("status").first()).toContainText("Ảnh 2/8");
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Xem toàn màn hình", exact: true }),
  ).toBeFocused();
  await page.getByRole("button", { name: "Mở menu", exact: true }).click();
  await expect(
    page
      .getByRole("dialog", { name: "Menu công khai" })
      .getByRole("link", { name: "Trang chủ", exact: true }),
  ).toHaveCount(0);
  await expect(
    page
      .getByRole("dialog", { name: "Menu công khai" })
      .getByRole("group", { name: "Về Tinh Hoa Việt" }),
  ).toHaveCount(0);
});
