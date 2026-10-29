import { expect, test } from "@playwright/test";

test("account headers use the actual frame for all four membership ranks", async ({
  page,
}, testInfo) => {
  let tier = "MEMBER";
  await page.route("**/api/v1/memberships/me", async (route) => {
    await route.fulfill({
      json: {
        success: true,
        data: {
          tier,
          memberNumber: "THV-DEMO",
          status: "ACTIVE",
          expiresAt: null,
          plans: [],
          purchases: [],
        },
        meta: { request_id: "frame-test" },
      },
    });
  });
  await page.route("**/api/v1/vouchers/offer", async (route) => {
    await route.fulfill({
      json: { success: true, data: null, meta: { request_id: "frame-test" } },
    });
  });
  for (const [rank, frame, label] of [
    ["MEMBER", "bronze", "Đồng"],
    ["SILVER", "silver", "Bạc"],
    ["COMPANION", "gold", "Vàng"],
    ["PRESTIGE", "diamond", "Kim cương"],
  ] as const) {
    tier = rank;
    await page.goto("/local-preview?screen=applicant-home");
    const mobile = testInfo.project.name === "mobile-chrome";
    await page.goto(mobile ? "/membership" : "/");
    const frameGroup = page
      .getByRole(mobile ? "main" : "banner")
      .getByRole("group", { name: `Hạng ${label}` });
    await expect(frameGroup).toBeVisible();
    const image = frameGroup.locator(`img[src*="${frame}.png"]`);
    await expect(image).toBeVisible();
    await expect
      .poll(() =>
        image.evaluate((element: HTMLImageElement) => element.naturalWidth),
      )
      .toBeGreaterThan(0);
    if (testInfo.project.name === "desktop-chrome") {
      await page.goto("/workspace");
      const dashboardFrame = page
        .getByRole("banner")
        .getByRole("group", { name: `Hạng ${label}` });
      await expect(dashboardFrame).toBeVisible();
      await expect(dashboardFrame).toHaveCSS("width", "44px");
      await expect(
        dashboardFrame.locator(`img[src*="${frame}.png"]`),
      ).toBeVisible();
      await page.screenshot({
        path: testInfo.outputPath(`header-${frame}.png`),
      });
    }
  }
});
