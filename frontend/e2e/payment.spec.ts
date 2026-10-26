import { expect, test } from "@playwright/test";

const dossierId = "9155dbf5-bb3e-449d-8bf0-9572cc642cac";
const paymentOrderId = "a255dbf5-bb3e-449d-8bf0-9572cc642cac";

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-payment");
});

test("admin charges a funded wallet and applicant sees fee confirmation", async ({
  context,
  page,
}) => {
  await context.addCookies([
    {
      name: "cns_access",
      value: "e2e-super-admin-access",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "cns_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
    {
      name: "cns_refresh",
      value: "e2e-refresh",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "cns_e2e_persona",
      value: "super-admin",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
  await page.goto("/admin/payments");
  const dossierField = page.getByLabel("Hồ sơ đã phê duyệt");
  const amountField = page.getByLabel("Số phí cần thu (VND)");
  await expect(dossierField).toBeVisible();
  await dossierField.selectOption(dossierId);
  await amountField.fill("1500000");
  await expect(dossierField).toHaveValue(dossierId);
  await expect(amountField).toHaveValue("1500000");
  const issueFeeButton = page.getByRole("button", {
    name: "Gửi thông báo thu phí",
  });
  await expect(issueFeeButton).toBeEnabled();
  await issueFeeButton.click();
  await expect(page.getByText("Đã trừ phí từ ví người nộp")).toBeVisible();
  await expect(page.getByText(/1\.500\.000 VND/)).toBeVisible();

  await context.clearCookies();
  await context.addCookies([
    {
      name: "cns_access",
      value: "e2e-access",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "cns_e2e_persona",
      value: "applicant",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
  await page.goto(`/dossiers/${dossierId}`);
  await expect(page.getByText("Thanh toán đã được xác nhận")).toBeVisible();

  await page.goto(`/payments/${paymentOrderId}`);
  await expect(
    page.getByRole("heading", { name: "Thanh toán thành công" }),
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Khoản phí đã được xác nhận")).toBeVisible();
  await expect(page.getByText("1.500.000 ₫")).toBeVisible();
  await expect(page.locator(".payment-workspace")).not.toContainText(
    /PayOS|QR/i,
  );
});
