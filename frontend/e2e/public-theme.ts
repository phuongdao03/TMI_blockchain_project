import type { Page } from "@playwright/test";

export async function selectPublicTheme(
  page: Page,
  label: "Giao diện sáng" | "Giao diện tối",
) {
  if ((page.viewportSize()?.width ?? 1280) <= 608) {
    await page.getByRole("button", { name: "Mở menu" }).click();
    await page
      .getByRole("navigation", { name: "Điều hướng di động" })
      .getByRole("button", { name: label })
      .click();
    await page.getByRole("button", { name: "Đóng menu" }).first().click();
    return;
  }

  await page
    .locator(".public-header__actions")
    .getByRole("button", { name: label })
    .click();
}
