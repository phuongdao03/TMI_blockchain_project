import { expect, test } from "@playwright/test";

const tiers = [
  { tier: "MEMBER", label: "Thành viên", cardLabel: "Đồng" },
  { tier: "COMPANION", label: "Đồng hành", cardLabel: "Vàng" },
  { tier: "PRESTIGE", label: "Tinh hoa", cardLabel: "Kim cương" },
] as const;

for (const { tier, label, cardLabel } of tiers) {
  test(`${label} card fits requested viewports and enforces room access`, async ({
    page,
    context,
  }, info) => {
    await context.addCookies([
      {
        name: "cns_access",
        value: "e2e-access",
        domain: "127.0.0.1",
        path: "/",
        httpOnly: true,
      },
      {
        name: "cns_refresh",
        value: "e2e-refresh",
        domain: "127.0.0.1",
        path: "/",
        httpOnly: true,
      },
      { name: "cns_csrf", value: "e2e-csrf", domain: "127.0.0.1", path: "/" },
    ]);
    const envelope = (data: unknown) => ({
      success: true,
      data,
      meta: { request_id: "membership-e2e-fixture" },
    });
    await page.route("**/api/v1/memberships/me", (route) =>
      route.fulfill({
        json: envelope({
          tier,
          memberNumber: "THV-123456789ABC",
          status: tier === "MEMBER" ? "FREE" : "ACTIVE",
          expiresAt: tier === "MEMBER" ? null : "2030-12-31T00:00:00Z",
          plans: [],
          purchases: [],
        }),
      }),
    );
    await page.route("**/api/v1/community/chat/*/messages", (route) =>
      route.fulfill({ json: envelope([]) }),
    );
    await page.route("**/api/v1/community/chat/*/access", (route) =>
      route.fulfill({
        json: envelope({
          room: "PRESTIGE",
          allowed: tier === "PRESTIGE",
          source: tier === "PRESTIGE" ? "TIER" : "NONE",
        }),
      }),
    );
    await page.route("**/api/v1/wallet", (route) =>
      route.fulfill({
        json: envelope({
          balanceMinor: 0,
          currency: "VND",
          provider: "mock",
          transactions: [],
          topups: [],
        }),
      }),
    );
    await page.goto("/membership");
    const card = page.getByRole("article", {
      name: new RegExp(`Thẻ ${cardLabel} của`),
    });
    await expect(card).toBeVisible();
    await expect(card).toContainText("THV-123456789ABC");
    await expect(
      page.getByText(/Tổng điểm|Số dư Affiliate|Tổng hoá đơn/),
    ).toHaveCount(0);
    for (const width of [360, 375, 390, 430, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 950 });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await expect(card).toBeVisible();
      if (width === 390 || width === 1440)
        await card.screenshot({
          path: info.outputPath(`card-${tier}-${width}.png`),
        });
      if (width === 390 || width === 1440)
        await page.screenshot({
          path: info.outputPath(`membership-${tier}-${width}.png`),
          fullPage: true,
        });
      if (width === 390) {
        const roomNavigation = page.getByRole("navigation", {
          name: "Các phòng hội viên",
        });
        await roomNavigation.scrollIntoViewIfNeeded();
        for (const button of await roomNavigation.getByRole("button").all()) {
          const bounds = await button.boundingBox();
          expect(bounds?.width).toBeGreaterThan(250);
          expect(bounds?.height).toBeLessThan(100);
        }
        await roomNavigation.screenshot({
          path: info.outputPath(`rooms-${tier}-390.png`),
        });
      }
    }
    await page.getByRole("button", { name: "Phòng Tinh hoa" }).click();
    if (tier !== "PRESTIGE") {
      await expect(
        page.getByText(/Phòng này dành cho hạng Kim cương trở lên/),
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Gửi tin nhắn" }),
      ).toHaveCount(0);
    } else {
      await expect(
        page.getByRole("textbox", { name: /Tin nhắn/ }),
      ).toBeVisible();
    }
    await page.goto("/wallet?returnTo=%2Fmembership");
    await expect(
      page.getByRole("main").getByRole("heading", { name: "Ví của tôi" }),
    ).toBeVisible();
    await expect(page.getByText(/Môi trường thử nghiệm/)).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Quay lại khoản cần thanh toán" }),
    ).toHaveAttribute("href", "/membership");
  });
}
