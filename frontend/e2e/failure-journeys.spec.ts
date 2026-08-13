import { expect, test } from "@playwright/test";

const mockApi = "http://127.0.0.1:4010";
const dossierId = "9155dbf5-bb3e-449d-8bf0-9572cc642cac";
const paymentOrderId = "a255dbf5-bb3e-449d-8bf0-9572cc642cac";

test.beforeEach(async ({ context }) => {
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
});

test("supplement request remains recoverable for the applicant", async ({
  page,
  request,
}) => {
  await request.post(`${mockApi}/api/e2e/reset-needs-supplement`);

  const response = await request.get(
    `${mockApi}/api/v1/dossiers/${dossierId}`,
    {
      headers: { Cookie: "tmi_access=e2e-access" },
    },
  );
  expect(response.ok()).toBeTruthy();
  expect((await response.json()).data.status).toBe("NEEDS_SUPPLEMENT");

  await page.goto(`/dossiers/${dossierId}`);
  await expect(page.locator("main")).toBeVisible();
});

test("expired payment gives a clear stopped state", async ({
  page,
  request,
}) => {
  await request.post(`${mockApi}/api/e2e/reset-payment-expired`);
  await page.goto(`/payments/${paymentOrderId}`);

  await expect(page.locator('main [role="alert"]')).toBeVisible();
  await expect(
    page.getByText("PAY-2026-E2E00002", { exact: true }),
  ).toBeVisible();
});

test("provider outage exposes a retry action", async ({ page, request }) => {
  await request.post(`${mockApi}/api/e2e/reset-payment-outage`);
  await page.goto(`/payments/${paymentOrderId}`);

  await expect(page.locator('main [role="alert"]')).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.locator("main button")).toBeVisible();
});

test("failed chain transaction can be queued for retry", async ({
  request,
}) => {
  const response = await request.post(
    `${mockApi}/api/v1/admin/blockchain/transactions/failure-e2e/retry`,
    {
      headers: {
        Cookie: "tmi_access=e2e-access; tmi_csrf=e2e-csrf",
        "X-CSRF-Token": "e2e-csrf",
      },
    },
  );

  expect(response.status()).toBe(202);
  expect((await response.json()).data.status).toBe("QUEUED");
});
