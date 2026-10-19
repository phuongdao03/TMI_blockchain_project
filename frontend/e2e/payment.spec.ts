import { expect, test } from "@playwright/test";

const dossierId = "9155dbf5-bb3e-449d-8bf0-9572cc642cac";

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-payment");
});

test("admin issues exact fee, applicant pays, blockchain issuance is queued", async ({
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
  const issueButton = page.getByRole("button", {
    name: "Gửi yêu cầu thanh toán",
  });
  await expect(dossierField).toBeVisible();
  await dossierField.selectOption(dossierId);
  await amountField.fill("1500000");
  await expect(dossierField).toHaveValue(dossierId);
  await expect(amountField).toHaveValue("1500000");
  await expect(issueButton).toBeEnabled();
  await issueButton.click();
  await expect(page.getByText("Đã gửi yêu cầu cho người nộp")).toBeVisible();
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
  await expect(page.getByText(/1\.500\.000 VND/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Tiếp tục thanh toán" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Tiếp tục thanh toán" }).click();
  await expect(page).toHaveURL(/\/payments\/[a-f0-9-]+$/);
  await expect(
    page.getByRole("link", { name: "Mở trang thanh toán bảo mật" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Thanh toán thành công" }),
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.locator(".payment-workspace")).not.toContainText(/PayOS/i);
});
