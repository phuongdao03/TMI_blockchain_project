import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { expectDocumentToFit } from "./responsive-layout";

test("home prioritizes evidence and fits every target width in both themes", async ({
  page,
}, info) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));
  await page.goto("/");
  const sections = page.locator(".public-home > section");
  await expect(sections.nth(1)).toHaveAttribute("id", "van-ban-thanh-lap");
  await expect(sections.nth(2)).toHaveAttribute("id", "thu-vien-anh");
  for (const theme of ["Giao diện sáng", "Giao diện tối"]) {
    if (
      !(await page
        .getByRole("button", { name: theme, exact: true })
        .first()
        .isVisible())
    ) {
      await page.getByRole("button", { name: "Mở menu", exact: true }).click();
    }
    await page
      .getByRole("button", { name: theme, exact: true })
      .first()
      .click();
    if (
      await page
        .getByRole("button", { name: "Đóng menu", exact: true })
        .isVisible()
    )
      await page.keyboard.press("Escape");
    for (const width of [320, 360, 375, 390, 414, 430, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await expectDocumentToFit(page, `${theme} homepage at ${width}`);
      if (width <= 430) {
        const box = await page
          .locator(".registry-hero__buttons .registry-button-primary")
          .boundingBox();
        expect(box?.width).toBeGreaterThanOrEqual(width - 44);
        await expect(page.locator(".registry-hero__copy--desktop")).toHaveCSS(
          "font-size",
          "16px",
        );
      }
      if (width === 390 || width === 1440) {
        for (const [name, selector] of [
          ["hero", ".registry-hero"],
          ["decision", "#van-ban-thanh-lap"],
          ["gallery", "#thu-vien-anh"],
          ["footer", ".public-footer"],
        ] as const) {
          await page.locator(selector).scrollIntoViewIfNeeded();
          await page.screenshot({
            path: info.outputPath(`${name}-${theme}-${width}.png`),
          });
        }
        await page.evaluate(() =>
          window.scrollTo({ top: 0, behavior: "instant" }),
        );
        await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
        const scan = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
          .analyze();
        expect(scan.violations).toEqual([]);
      }
    }
  }
  expect(
    requests.filter(
      (url) =>
        url.endsWith("decision.pdf") || url.endsWith("proposal-2026.pdf"),
    ),
  ).toEqual([]);
  expect(pageErrors).toEqual([]);
});

test("founding PDF opens, renders both real pages, zooms and returns focus", async ({
  page,
}, info) => {
  await page.emulateMedia({
    colorScheme: info.project.name === "mobile-chrome" ? "dark" : "light",
  });
  await page.goto("/");
  const opener = page
    .getByRole("button", { name: "Xem văn bản đầy đủ", exact: true })
    .last();
  await opener.click();
  const dialog = page.getByRole("dialog", {
    name: "Quyết định số 55 — Văn bản thành lập",
  });
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("img", { name: "Trang 1 của Quyết định số 55" }),
  ).toBeVisible();
  await expect(dialog.getByText("Đang tải trang văn bản…")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Trang sau", exact: true }).click();
  await expect(
    dialog.getByRole("img", { name: "Trang 2 của Quyết định số 55" }),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "Phóng to văn bản" }).click();
  await expect(
    dialog.getByRole("button", { name: "Vừa khung văn bản" }),
  ).toHaveText("125%");
  await page.screenshot({ path: info.outputPath("decision-page-2.png") });
  expect(
    (
      await new AxeBuilder({ page })
        .include(".public-media-dialog")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(opener).toBeFocused();
});

test("gallery filters, swipes, zooms and restores focus without losing its selection", async ({
  page,
}, info) => {
  await page.emulateMedia({
    colorScheme: info.project.name === "mobile-chrome" ? "dark" : "light",
  });
  await page.goto("/");
  await page.locator("#thu-vien-anh").scrollIntoViewIfNeeded();
  await expect(
    page.locator(".heritage-gallery__thumbnails button"),
  ).toHaveCount(6, { timeout: 60_000 });
  if (await page.getByLabel("Chọn bộ ảnh").isVisible())
    await page.getByLabel("Chọn bộ ảnh").selectOption("Văn hóa & đời sống");
  else await page.getByRole("button", { name: /Văn hóa & đời sống/ }).click();
  const opener = page.getByRole("button", { name: /Khám phá tất cả hình ảnh/ });
  await expect(page.locator(".heritage-gallery__counter")).toContainText("08");
  await opener.click();
  const dialog = page.getByRole("dialog", { name: "Ảnh Tinh Hoa Việt" });
  await expect(dialog.getByText("Ảnh 1/8")).toBeVisible();
  const viewport = dialog.locator(".heritage-lightbox__viewport");
  await viewport.dispatchEvent("touchstart", {
    touches: [{ identifier: 1, clientX: 250, clientY: 100 }],
  });
  await viewport.dispatchEvent("touchend", {
    changedTouches: [{ identifier: 1, clientX: 100, clientY: 105 }],
  });
  await expect(dialog.getByText("Ảnh 2/8")).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(dialog.getByText("Ảnh 3/8")).toBeVisible();
  await dialog.getByRole("button", { name: "Phóng to ảnh" }).click();
  await expect(
    dialog.getByRole("button", { name: "Phóng to ảnh" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.setViewportSize({ width: 320, height: 700 });
  await expectDocumentToFit(page, "Gallery dialog at 320px");
  await page.screenshot({ path: info.outputPath("gallery-mobile-dialog.png") });
  expect(
    (
      await new AxeBuilder({ page })
        .include(".public-media-dialog")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await dialog.getByRole("button", { name: "Đóng ảnh toàn màn hình" }).click();
  await expect(opener).toBeFocused();
  await expect(page.getByLabel("Chọn bộ ảnh")).toHaveValue(
    "Văn hóa & đời sống",
  );
  await expect(page.locator("body")).not.toHaveCSS("overflow", "hidden");
});

test("proposal reads inline and preserves its existing reader controls", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("region", { name: "Trình xem proposal", exact: true }),
  ).toHaveCount(0);
  await page.locator(".proposal-inline").scrollIntoViewIfNeeded();
  const dialog = page.getByRole("region", {
    name: "Trình xem proposal",
    exact: true,
  });
  await expect(
    dialog.getByRole("img", { name: /trang 1 trên 53/ }),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "Trang sau", exact: true }).click();
  await expect(
    dialog.getByRole("img", { name: /trang 2 trên 53/ }),
  ).toBeVisible();
  await dialog
    .getByRole("button", { name: "Phóng to trang", exact: true })
    .click();
  await expect(
    dialog.getByRole("button", { name: "Đặt lại mức phóng to" }),
  ).toContainText("125%");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeVisible();
});

test("PDF failure offers recovery without trapping the visitor", async ({
  page,
}) => {
  await page.route("**/assets/institution/decision.pdf", (route) =>
    route.fulfill({ status: 503, body: "Unavailable" }),
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Xem văn bản đầy đủ", exact: true })
    .last()
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("alert")).toContainText(
    "Chưa xem được văn bản",
  );
  await expect(
    dialog.getByRole("link", { name: "Mở bằng trình duyệt" }),
  ).toHaveAttribute("href", "/assets/institution/decision.pdf");
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
});

test("gallery image failure can retry the real image", async ({ page }) => {
  await page.goto("/");
  await expect
    .poll(() =>
      page
        .locator(".heritage-gallery__stage img")
        .evaluate(
          (image) =>
            (image as HTMLImageElement).complete &&
            (image as HTMLImageElement).naturalWidth > 0,
        ),
    )
    .toBe(true);
  await page.route("**/_next/image**", (route) => {
    const source = new URL(route.request().url()).searchParams.get("url") ?? "";
    return source.includes("gallery-")
      ? route.fulfill({ status: 503, body: "Unavailable" })
      : route.continue();
  });
  if (await page.getByLabel("Chọn bộ ảnh").isVisible())
    await page.getByLabel("Chọn bộ ảnh").selectOption("Văn hóa & đời sống");
  else await page.getByRole("button", { name: /Văn hóa & đời sống/ }).click();
  await expect(page.locator(".heritage-gallery__error")).toContainText(
    "Chưa thể tải ảnh",
  );
  await page.unroute("**/_next/image**");
  await page.getByRole("button", { name: "Thử tải lại ảnh" }).click();
  await expect
    .poll(() =>
      page
        .locator(".heritage-gallery__stage img")
        .evaluate(
          (image) =>
            (image as HTMLImageElement).complete &&
            (image as HTMLImageElement).naturalWidth > 0,
        ),
    )
    .toBe(true);
  await expect(page.locator(".heritage-gallery__error")).toHaveCount(0);
});
