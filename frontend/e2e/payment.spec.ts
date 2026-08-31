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
      name: "tmi_access",
      value: "e2e-super-admin-access",
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
    {
      name: "tmi_refresh",
      value: "e2e-refresh",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "tmi_e2e_persona",
      value: "super-admin",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
  await page.goto("/admin/payments");
  await page.getByLabel("Mã hồ sơ").fill(dossierId);
  await page.getByLabel("Số tiền cần thanh toán (VND)").fill("1500000");
  await page.getByRole("button", { name: "Gửi yêu cầu thanh toán" }).click();
  await expect(page.getByText("Đã gửi yêu cầu cho người nộp")).toBeVisible();
  await expect(page.getByText(/1\.500\.000 VND/)).toBeVisible();

  await context.clearCookies();
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
      name: "tmi_e2e_persona",
      value: "applicant",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
  await page.goto(`/dossiers/${dossierId}`);
  await expect(page.getByText(/1\.500\.000 VND/)).toBeVisible();
  await page.getByRole("link", { name: "Xem và thanh toán qua PayOS" }).click();
  await expect(
    page.getByRole("heading", { name: "Thanh toán thành công" }),
  ).toBeVisible({ timeout: 10_000 });
});
