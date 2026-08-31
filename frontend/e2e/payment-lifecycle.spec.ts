import { expect, test } from "@playwright/test";

const mockApi = `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? 4010}`;
const paymentOrderId = "a255dbf5-bb3e-449d-8bf0-9572cc642cac";

test.beforeEach(async ({ context, request }) => {
  await context.addCookies([
    {
      name: "tmi_access",
      value: "e2e-access",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "tmi_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
  await request.post(`${mockApi}/api/e2e/reset-payment-pending`);
});

test("applicant safely cancels a pending payOS checkout on mobile", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chrome");
  await page.goto(`/payments/${paymentOrderId}`);

  await expect(
    page.getByRole("link", { name: "Mở trang thanh toán bảo mật" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Hủy lần thanh toán" }).click();
  await page
    .getByLabel("Lý do hủy")
    .fill("Tôi cần kiểm tra lại thông tin hồ sơ");
  await page.getByRole("button", { name: "Xác nhận hủy" }).click();

  await expect(page.getByText("Đã hủy", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Bạn đã hủy lần thanh toán này"),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
