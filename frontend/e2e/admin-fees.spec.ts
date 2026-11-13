import { expect, test } from "@playwright/test";

test("Admin reviews and schedules a global submission fee", async ({
  context,
  page,
}) => {
  await context.addCookies(
    (
      [
        ["cns_access", "e2e-super-admin-access"],
        ["cns_csrf", "e2e-csrf"],
      ] as const
    ).map(([name, value]) => ({
      name,
      value,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax" as const,
    })),
  );

  let policy: Record<string, unknown> | null = null;
  const envelope = (data: unknown) => ({
    success: true,
    data,
    meta: { request_id: "admin-fee-fixture" },
  });
  await page.route("**/api/v1/admin/fee-policies**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "GET") {
      await route.fulfill({ json: envelope(policy ? [policy] : []) });
      return;
    }
    const input = request.postDataJSON() as Record<string, unknown>;
    if (url.pathname.endsWith("/approve")) {
      expect(input.confirmActivation).toBe(true);
      policy = {
        ...(policy ?? {}),
        status: "SCHEDULED",
        approvedByUserId: "admin-1",
      };
      await route.fulfill({ json: envelope(policy) });
      return;
    }
    expect(input).toMatchObject({
      feeType: "DOSSIER_SUBMISSION",
      amountMinor: 5_000_000,
    });
    policy = {
      id: "policy-1",
      feeType: "DOSSIER_SUBMISSION",
      dossierTypeId: null,
      versionNo: 1,
      amountMinor: 5_000_000,
      currency: "VND",
      displayName: "Phí nộp hồ sơ",
      reason: "Mức phí nộp hồ sơ chung",
      startsAt: input.startsAt,
      endsAt: null,
      status: "DRAFT",
      createdByUserId: "admin-1",
      approvedByUserId: null,
      approvedAt: null,
    };
    await route.fulfill({ status: 201, json: envelope(policy) });
  });
  await page.route("**/api/v1/admin/fee-waivers**", (route) =>
    route.fulfill({ json: envelope([]) }),
  );

  await page.goto("/admin/payments");
  await expect(page.getByText("Chưa có mức phí hiệu lực")).toBeVisible();
  await page.getByRole("button", { name: "Thay đổi mức phí" }).click();
  await page.getByLabel("Bắt đầu áp dụng").fill("2026-11-14T00:00");
  await page.getByLabel("Căn cứ / lý do").fill("Mức phí nộp hồ sơ chung");
  await page.getByRole("button", { name: "Tạo bản nháp" }).click();

  await expect(page.getByText("Xem lại trước khi kích hoạt")).toBeVisible();
  await expect(page.getByText("5.000.000 ₫", { exact: true })).toBeVisible();
  const confirm = page.getByRole("button", { name: "Xác nhận kích hoạt" });
  await expect(confirm).toBeDisabled();
  await page.getByRole("checkbox").check();
  await expect(confirm).toBeEnabled();
  await confirm.click();
  await expect(page.getByText("5.000.000 ₫", { exact: true })).toBeVisible();
  await expect(page.getByText("Đã lên lịch").first()).toBeVisible();
});
