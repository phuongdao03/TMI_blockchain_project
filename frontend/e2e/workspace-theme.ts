import { expect, type Page } from "@playwright/test";

export async function selectWorkspaceTheme(
  page: Page,
  label: "Giao diện sáng" | "Giao diện tối",
) {
  const mobileWorkspace = (page.viewportSize()?.width ?? 1280) <= 672;
  if (!mobileWorkspace) {
    await page
      .locator(".dashboard-context-header__desktop-account")
      .getByRole("button", { name: label })
      .click();
    return;
  }

  const adminArea = new URL(page.url()).pathname.startsWith("/admin");
  const navigationContext = adminArea ? "quản trị" : "workspace";
  const trigger = page.getByRole("button", {
    name: `Mở điều hướng ${navigationContext}`,
  });
  const drawer = page.getByRole("dialog", {
    name: `Điều hướng ${navigationContext}`,
  });
  await expect(async () => {
    if (!(await drawer.isVisible())) await trigger.click();
    await expect(drawer).toBeVisible({ timeout: 3_000 });
  }).toPass({ timeout: 20_000 });
  await drawer.getByRole("button", { name: label }).click();
  await page.keyboard.press("Escape");
}
