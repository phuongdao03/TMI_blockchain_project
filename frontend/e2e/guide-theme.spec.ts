import { expect, test } from "@playwright/test";

test("guide actions keep readable colors in both themes", async ({ page }) => {
  await page.goto("/guide");

  const primary = page.getByRole("link", { name: "Xem đề cử" });
  const secondary = page.getByRole("link", { name: "Theo dõi hồ sơ" });

  await page.getByRole("button", { name: "Giao diện sáng" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(primary).toHaveCSS("background-color", "rgb(101, 0, 0)");
  await expect(primary).toHaveCSS("color", "rgb(255, 255, 255)");
  await secondary.hover();
  await expect(secondary).toHaveCSS("color", "rgb(157, 0, 0)");

  await page.getByRole("button", { name: "Giao diện tối" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(primary).toHaveCSS("background-color", "rgb(246, 197, 21)");
  await expect(primary).toHaveCSS("color", "rgb(36, 21, 21)");
  await secondary.hover();
  await expect(secondary).toHaveCSS("color", "rgb(246, 197, 21)");
});
