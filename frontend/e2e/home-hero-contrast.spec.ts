import { expect, test } from "@playwright/test";

test("light home hero keeps its information summary readable", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.getByRole("button", { name: "Giao diện sáng" }).click();

  const summaryDetails = page.locator(".registry-hero__summary dd");

  await expect(summaryDetails.first()).toHaveCSS("color", "rgb(255, 255, 255)");
});
