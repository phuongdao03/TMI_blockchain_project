import { expect, test } from "@playwright/test";

test("Admin applies a global submission fee immediately", async ({
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
  let applyRequestCount = 0;
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

    expect(request.method()).toBe("PUT");
    expect(url.pathname).toBe("/api/v1/admin/fee-policies/submission/current");
    const input = request.postDataJSON() as Record<string, unknown>;
    expect(input).toEqual({ amountMinor: 5_000_000 });
    applyRequestCount += 1;
    policy = {
      id: "policy-1",
      feeType: "DOSSIER_SUBMISSION",
      dossierTypeId: null,
      versionNo: 1,
      amountMinor: input.amountMinor,
      currency: "VND",
      displayName: "Submission fee",
      reason: "Immediate administrator update",
      startsAt: "2026-11-14T00:00:00Z",
      endsAt: null,
      status: "ACTIVE",
      createdByUserId: "admin-1",
      approvedByUserId: "admin-1",
      approvedAt: "2026-11-14T00:00:00Z",
    };
    await route.fulfill({ json: envelope(policy) });
  });
  await page.route("**/api/v1/admin/fee-waivers**", (route) =>
    route.fulfill({ json: envelope([]) }),
  );

  await page.goto("/admin/payments");
  const amount = page.locator('input[type="number"]').first();
  await expect(amount).toHaveValue("5000000");
  await page
    .locator("form")
    .filter({ has: amount })
    .getByRole("button")
    .click();
  await expect(page.locator("#current-submission-fee-title")).toContainText(
    "5.000.000",
  );
  expect(applyRequestCount).toBe(1);
});
