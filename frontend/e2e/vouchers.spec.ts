import { expect, test } from "@playwright/test";

for (const colorScheme of ["light", "dark"] as const) {
  test(`login voucher can be claimed and remains saved after reload (${colorScheme})`, async ({
    page,
  }, testInfo) => {
    await page.emulateMedia({ colorScheme });
    let claimed = false;
    const offer = {
      id: "50e981db-3cc9-478b-859e-315f582f5145",
      title: "Tinh Hoa Việt gửi tặng bạn 200.000đ!",
      description:
        "Cảm ơn bạn đã đồng hành cùng Tinh Hoa Việt. Nhận món quà tri ân và lưu vào tài khoản của bạn.",
      terms:
        "Ưu đãi dành cho phí hồ sơ đề cử, áp dụng một lần. Không quy đổi thành tiền mặt. Chức năng áp dụng khi thanh toán sẽ được thông báo sau.",
      imagePath: "/images/promotions/golden-voucher.png",
      amountVnd: 200000,
      validityDays: 60,
    };
    const saved = {
      ...offer,
      id: "saved-voucher",
      campaignId: offer.id,
      claimedAt: "2026-10-29T00:00:00Z",
      expiresAt: "2026-12-28T00:00:00Z",
      expired: false,
    };
    await page.route("**/api/v1/vouchers/**", async (route) => {
      const url = new URL(route.request().url());
      let data: unknown = null;
      if (url.pathname.endsWith("/offer")) data = claimed ? null : offer;
      if (url.pathname.endsWith("/mine")) data = claimed ? [saved] : [];
      if (url.pathname.endsWith("/claim")) {
        expect(route.request().method()).toBe("POST");
        expect(route.request().headers()["x-csrf-token"]).toBe("e2e-csrf");
        claimed = true;
        data = saved;
      }
      await route.fulfill({
        json: { success: true, data, meta: { request_id: "voucher-e2e" } },
      });
    });
    await page.goto("/login?accountType=INDIVIDUAL_APPLICANT");
    await page
      .getByRole("textbox", { name: "Email" })
      .fill("applicant@tinhhoaviet.org.vn");
    await page
      .getByLabel("Mật khẩu", { exact: true })
      .fill("correct horse battery staple");
    await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
    await expect(page).toHaveURL(/\/workspace$/, { timeout: 60_000 });
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    const image = dialog.getByRole("img");
    await expect(image).toBeVisible();
    await expect
      .poll(() => image.evaluate((node: HTMLImageElement) => node.naturalWidth))
      .toBeGreaterThan(0);
    const button = dialog.getByRole("button", { name: "Nhận voucher ngay" });
    await expect(button).toHaveCSS("background-color", "rgb(157, 0, 0)");
    await expect(button).toHaveCSS("color", "rgb(255, 255, 255)");
    if (testInfo.project.name === "desktop-chrome") {
      await button.hover();
      await expect(button).toHaveCSS("background-color", "rgb(122, 0, 0)");
    }
    await expect(button).toBeInViewport();
    await page.screenshot({ path: testInfo.outputPath("login-voucher.png") });
    // Native dialog must keep keyboard focus inside the modal.
    await button.focus();
    for (let i = 0; i < 5; i++) await page.keyboard.press("Tab");
    expect(
      await dialog.evaluate((node) => node.contains(document.activeElement)),
    ).toBe(true);
    await button.click();
    await expect(
      dialog.getByRole("heading", { name: "Đã nhận voucher!" }),
    ).toBeVisible();
    await dialog.getByRole("link", { name: "Xem voucher của tôi" }).click();
    await expect(page).toHaveURL(/\/vouchers$/);
    await expect(
      page
        .locator("#main-content")
        .getByRole("heading", { name: "Voucher của tôi", exact: true }),
    ).toBeVisible();
    await expect(page.getByText(offer.title, { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByText(offer.title, { exact: true })).toBeVisible();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });
}
