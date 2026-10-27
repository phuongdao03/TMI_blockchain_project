import { expect, test } from "@playwright/test";

test("owner can follow ordinary publication or promote the same older dossier", async ({
  page,
  context,
}, info) => {
  await context.addCookies(
    (
      [
        ["cns_access", "e2e-access"],
        ["cns_refresh", "e2e-refresh"],
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
  const id = "2155dbf5-bb3e-449d-8bf0-9572cc642cac";
  let status = "PAID";
  const envelope = (data: unknown) => ({
    success: true,
    data,
    meta: { request_id: "promotion-fixture" },
  });
  const detail = () => ({
    id,
    ownerUserId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
    code: "THV-2026-OLD",
    title: "Di sản cần quảng bá",
    status,
    visibility: "PUBLIC",
    canEdit: false,
    currentVersionNo: 1,
    summary: "Tư liệu văn hóa",
    formData: {},
    documentRules: [],
    evidences: [],
    createdAt: "2026-10-01T00:00:00Z",
    updatedAt: "2026-10-27T00:00:00Z",
    submissionFeeRequired: true,
    submissionFeePaidAt: "2026-10-01T00:00:00Z",
  });
  await page.route(`**/api/v1/dossiers/${id}`, (route) =>
    route.fulfill({ json: envelope(detail()) }),
  );
  await page.route(`**/api/v1/dossiers/${id}/versions`, (route) =>
    route.fulfill({ json: envelope([]) }),
  );
  await page.route(`**/api/v1/dossiers/${id}/timeline`, (route) =>
    route.fulfill({ json: envelope([]) }),
  );
  await page.route("**/api/v1/dossiers?*", (route) =>
    route.fulfill({
      json: { ...envelope([]), meta: { page: 1, pageSize: 100, total: 101 } },
    }),
  );
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`/dossiers/${id}`);
  await page
    .getByRole("link", { name: "Theo dõi công bố thông thường" })
    .click();
  await expect(page.locator("#dossier-publication-progress")).toBeInViewport();
  await expect(
    page.getByText(/Quảng cáo không phải điều kiện công bố/),
  ).toBeVisible();
  status = "PUBLISHED";
  await page.reload();
  await page
    .getByRole("link", { name: "Quảng bá hồ sơ này" })
    .scrollIntoViewIfNeeded();
  await page.screenshot({
    path: `../docs/ux-evidence-2026-10-27/promotion-${info.project.name}.png`,
    fullPage: true,
    scale: "css",
  });
  await page.getByRole("link", { name: "Quảng bá hồ sơ này" }).click();
  await expect(page).toHaveURL(new RegExp(`/advertising\\?dossierId=${id}`));
  await expect(
    page.getByLabel("Hồ sơ muốn quảng bá", { exact: false }),
  ).toHaveValue(id);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});
