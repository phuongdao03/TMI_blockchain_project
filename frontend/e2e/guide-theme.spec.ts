import { expect, test } from "@playwright/test";

import { selectPublicTheme } from "./public-theme";

test("guide actions keep readable colors in both themes", async ({ page }) => {
  await page.route("**/api/v1/public/guide/articles*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: [
          {
            id: "guide-e2e-1",
            title: "Hướng dẫn tra cứu",
            slug: "huong-dan-tra-cuu",
            summary: "Cách tìm nội dung đã công bố.",
            category: "getting-started",
            audiences: ["PUBLIC"],
            bodyHtml: "<h2>Bắt đầu</h2><p>Mở thư viện.</p>",
            status: "PUBLISHED",
            sortOrder: 1,
            version: 1,
            readingMinutes: 1,
            publishedAt: "2026-01-01T00:00:00.000Z",
            createdAt: "2026-01-01T00:00:00.000Z",
            updatedAt: "2026-01-01T00:00:00.000Z",
          },
        ],
        meta: {
          requestId: "guide-theme-e2e",
          page: 1,
          pageSize: 100,
          total: 1,
        },
      }),
    }),
  );
  await page.goto("/guide");

  const primary = page.getByRole("button", { name: "Tìm", exact: true });
  const articleTitle = page.locator("#all-guides a h3").first();
  await expect(articleTitle).toBeVisible();
  const hasHover = await page.evaluate(
    () => window.matchMedia("(hover: hover)").matches,
  );

  await selectPublicTheme(page, "Giao diện sáng");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(primary).toHaveCSS("background-color", "rgb(157, 0, 0)");
  await expect(primary).toHaveCSS("color", "rgb(255, 255, 255)");
  await expect(articleTitle).toHaveCSS("color", "rgb(36, 21, 21)");
  if (hasHover) {
    await articleTitle.hover();
    await expect(articleTitle).toHaveCSS("color", "rgb(157, 0, 0)");
  }

  await selectPublicTheme(page, "Giao diện tối");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(primary).toHaveCSS("background-color", "rgb(246, 197, 21)");
  await expect(primary).toHaveCSS("color", "rgb(36, 21, 21)");
  await expect(articleTitle).toHaveCSS("color", "rgb(255, 249, 243)");
  if (hasHover) {
    await articleTitle.hover();
    await expect(articleTitle).toHaveCSS("color", "rgb(246, 197, 21)");
  }
});
