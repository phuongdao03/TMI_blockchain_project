import type { Page } from "@playwright/test";

export async function selectPublicTheme(
  page: Page,
  label: "Giao diện sáng" | "Giao diện tối",
) {
  if ((page.viewportSize()?.width ?? 1280) < 1024) {
    await page.getByRole("button", { name: "Mở điều hướng" }).click();
    await page
      .getByRole("dialog", { name: "Điều hướng công khai" })
      .getByRole("group", { name: "Chọn giao diện" })
      .getByRole("button", { name: label })
      .click();
    await page.getByRole("button", { name: "Đóng điều hướng" }).first().click();
    return;
  }

  await page
    .locator(".public-header__actions")
    .getByRole("button", { name: label })
    .click();
}
