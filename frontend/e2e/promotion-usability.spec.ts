import { expect, test } from "@playwright/test";
import { newCampaign } from "../src/lib/api/promotion-types";

test("an online customer sees a newly started campaign on the public home", async ({
  page,
}, testInfo) => {
  let live = false;
  const campaign = {
    ...newCampaign(),
    id: "live-gift",
    title: "Quà tri ân đang diễn ra",
    description: "Nhận ưu đãi dành cho tài khoản của bạn.",
  };
  await page.route("**/api/v1/vouchers/**", async (route) => {
    const url = new URL(route.request().url());
    await route.fulfill({
      json: {
        success: true,
        data: url.pathname.endsWith("/offer") && live ? campaign : null,
        meta: { request_id: "promotion-ui" },
      },
    });
  });
  await page.clock.install();
  await page.goto("/local-preview?screen=applicant-home");
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  live = true;
  const request = page.waitForRequest((req) =>
    req.url().includes("/vouchers/offer?trigger=DASHBOARD"),
  );
  await page.clock.fastForward(31_000);
  await request;
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading")).toHaveText(campaign.title);
  const cta = dialog.getByRole("button", {
    name: campaign.policy.presentation.primaryCta,
  });
  await expect(cta).toBeInViewport();
  await expect(cta).toHaveCSS("background-color", "rgb(157, 0, 0)");
  await page.screenshot({
    path: testInfo.outputPath("online-customer-popup.png"),
  });
});

for (const colorScheme of ["light", "dark"] as const) {
  test(`admin can publish and edit a campaign with readable controls (${colorScheme})`, async ({
    page,
  }, testInfo) => {
    await page.emulateMedia({ colorScheme });
    let campaign = {
      ...newCampaign(),
      id: "campaign-ui",
      name: "Chiến dịch tri ân",
      code: "GIFT_UI",
      title: "Quà tri ân",
      description: "Ưu đãi dành cho khách hàng",
      status: "DRAFT",
      policyVersion: 1,
      budgetReservedVnd: 0,
      budgetSpentVnd: 0,
      createdAt: "2026-10-29T00:00:00Z",
      updatedAt: "2026-10-29T00:00:00Z",
    };
    await page.route("**/api/v1/admin/promotions**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let data: unknown = campaign;
      if (path.endsWith("/publish"))
        campaign = { ...campaign, status: "ACTIVE" };
      if (route.request().method() === "PATCH")
        campaign = {
          ...campaign,
          ...route.request().postDataJSON(),
          policyVersion: 2,
        };
      data = path.endsWith("/promotions")
        ? { items: [campaign], total: 1, page: 1, pageSize: 20 }
        : campaign;
      await route.fulfill({
        json: {
          success: true,
          data,
          meta: { request_id: "promotion-admin-ui" },
        },
      });
    });
    await page.goto("/local-preview?screen=admin-promotions");
    await page.goto("/admin/promotions/campaigns");
    await expect(page.getByText(campaign.name, { exact: true })).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.getByRole("button", { name: "Xuất bản", exact: true }).click();
    const confirm = page
      .getByRole("dialog")
      .getByRole("button", { name: "Xác nhận", exact: true });
    await expect(confirm).toHaveCSS(
      "background-color",
      colorScheme === "dark" ? "rgb(246, 197, 21)" : "rgb(157, 0, 0)",
    );
    await expect(confirm).toHaveCSS(
      "color",
      colorScheme === "dark" ? "rgb(36, 21, 21)" : "rgb(255, 255, 255)",
    );
    await expect(confirm).toBeInViewport();
    await page.screenshot({
      path: testInfo.outputPath("publish-confirmation.png"),
    });
    await confirm.click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await page
      .getByRole("link", { name: "Mở chiến dịch", exact: true })
      .click();
    const name = page.getByRole("textbox", {
      name: "Tên chiến dịch",
      exact: true,
    });
    await expect(name).toBeEditable();
    await name.fill("Chiến dịch đã chỉnh sửa");
    await page.getByRole("button", { name: "Lưu thay đổi" }).click();
    await expect(
      page.getByText("Đã lưu chiến dịch.", { exact: true }),
    ).toBeVisible();
    expect(campaign.name).toBe("Chiến dịch đã chỉnh sửa");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.goto("/");
    expect(
      await page.locator('a[href="/vouchers"], a[href="/wallet"]').count(),
    ).toBe(0);
  });
}
