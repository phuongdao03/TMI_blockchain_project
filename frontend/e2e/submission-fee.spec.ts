import { expect, test } from "@playwright/test";

test("submission fee checkout can resume and payment leads to review", async ({
  page,
  context,
}, info) => {
  await context.addCookies(
    (
      [
        ["cns_access", "e2e-access"],
        ["cns_refresh", "e2e-refresh"],
        ["cns_csrf", "e2e-csrf"],
        ["cns_e2e_persona", "applicant"],
      ] as const
    ).map(([name, value]) => ({
      name,
      value,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax" as const,
    })),
  );
  const id = "9155dbf5-bb3e-449d-8bf0-9572cc642cac";
  const envelope = (data: unknown) => ({
    success: true,
    data,
    meta: { request_id: "submission-fee-fixture" },
  });
  const now = "2026-10-27T08:00:00Z";
  await page.route(`**/api/v1/dossiers/${id}`, (route) =>
    route.fulfill({
      json: envelope({
        id,
        code: "THV-2026-TEST",
        title: "Di sản làng nghề Việt",
        status: "PAYMENT_PENDING",
        submissionFeeRequired: true,
        submissionFeePaidAt: null,
        canEdit: false,
        currentVersionNo: 1,
        submittedAt: now,
        createdAt: now,
        updatedAt: now,
        summary: "Câu chuyện làng nghề",
        formData: {},
        visibility: "PRIVATE",
        evidences: [],
        documentRules: [],
      }),
    }),
  );
  await page.route(`**/api/v1/dossiers/${id}/submission-fee`, (route) =>
    route.fulfill({
      json: envelope({
        amountMinor: 5_000_000,
        currency: "VND",
        description: "Phí nộp hồ sơ đề cử",
      }),
    }),
  );
  await page.route(`**/api/v1/dossiers/${id}/active-payment-order`, (route) =>
    route.fulfill({ json: envelope({ id: "expired", status: "EXPIRED" }) }),
  );
  await page.route(
    `**/api/v1/dossiers/${id}/submission-payment`,
    async (route) => {
      expect(route.request().headers()["idempotency-key"]).toBeTruthy();
      await route.fulfill({
        json: envelope({ paymentOrderId: "submission-paid" }),
      });
    },
  );
  await page.route("**/api/v1/payment-orders/submission-paid", (route) =>
    route.fulfill({
      json: envelope({
        id: "submission-paid",
        dossierId: id,
        orderCode: "20261027",
        provider: "wallet",
        purpose: "SUBMISSION_FEE",
        status: "PAID",
        amountMinor: 5_000_000,
        currency: "VND",
        description: "Phí nộp hồ sơ đề cử",
        paidAt: now,
        createdAt: now,
        updatedAt: now,
        expiresAt: "2026-11-03T08:00:00Z",
      }),
    }),
  );
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`/dossiers/${id}`);
  const action = page.getByRole("button", {
    name: "Tiếp tục thanh toán phí nộp",
  });
  await expect(action).toBeVisible();
  await expect(
    page.getByText("Thanh toán phí nộp để bắt đầu thẩm định"),
  ).toBeVisible();
  for (const width of [360, 375, 390, 430, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    if ([390, 1440].includes(width))
      await page.screenshot({
        path: info.outputPath(`submission-fee-${width}.png`),
        fullPage: true,
        scale: "css",
      });
  }
  await page.setViewportSize({ width: 390, height: 900 });
  await action.click();
  await expect(page).toHaveURL(/\/payments\/submission-paid/);
  await expect(
    page.getByText(/Hồ sơ đã được tiếp nhận để kiểm tra và thẩm định/),
  ).toBeVisible();
  await expect(
    page.getByText(/đang chuẩn bị và phát hành bằng xác lập/),
  ).toHaveCount(0);
  expect(errors).toEqual([]);
});
