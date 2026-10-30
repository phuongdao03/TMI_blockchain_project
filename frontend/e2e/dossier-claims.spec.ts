import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import type { DossierClaim } from "../src/lib/api/types";

test("applicant links a private claim to an attached file and saves its revision", async ({
  context,
  page,
}, info) => {
  await context.addCookies(
    [
      ["cns_access", "e2e-access"],
      ["cns_refresh", "e2e-refresh"],
      ["cns_csrf", "e2e-csrf"],
      ["cns_e2e_persona", "applicant"],
    ].map(([name, value]) => ({
      name: name!,
      value: value!,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax" as const,
    })),
  );
  const dossierId = "9155dbf5-bb3e-449d-8bf0-9572cc642cac";
  let claims: DossierClaim[] = [];
  let revision = 0;
  const envelope = (data: unknown) => ({
    success: true,
    data,
    meta: { requestId: "claims-e2e" },
  });
  const detail = () => ({
    id: dossierId,
    code: "THV-2026-CLAIM",
    ownerUserId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
    organizationId: null,
    categoryId: "4d28db19-1507-5a45-a50d-cd0aa83029ec",
    dossierTypeId: null,
    dossierTypeVersionId: null,
    formData: {},
    title: "Hồ sơ nhận định và căn cứ",
    slug: null,
    summary: "Nguồn tư liệu gốc.",
    status: "DRAFT",
    visibility: "PRIVATE",
    currentVersionNo: 0,
    submittedAt: null,
    createdAt: "2026-10-30T00:00:00Z",
    updatedAt: "2026-10-30T00:00:00Z",
    canEdit: true,
    claims,
    claimsRevision: revision,
    documentRules: [],
    claimCriteria: [{ key: "ownership_basis", label: "Căn cứ quyền sử dụng" }],
    evidences: [
      {
        id: "evidence-claim-1",
        dossierId,
        dossierVersionId: null,
        mediaAssetId: "media-claim-1",
        evidenceType: "PRIMARY",
        evidenceRole: "PRIMARY",
        accessScope: "PRIVATE",
        title: "Bản thảo gốc",
        description: null,
        issuedAt: null,
        displayOrder: 0,
        isPublic: false,
        mimeType: "application/pdf",
        bytes: 1024,
        sha256: "a".repeat(64),
      },
    ],
  });
  await page.route(`**/api/v1/dossiers/${dossierId}`, async (route) => {
    await route.fulfill({ json: envelope(detail()) });
  });
  for (const suffix of ["versions", "timeline"])
    await page.route(`**/api/v1/dossiers/${dossierId}/${suffix}`, (route) =>
      route.fulfill({ json: envelope([]) }),
    );
  await page.route(`**/api/v1/dossiers/${dossierId}/claims`, async (route) => {
    const body = route.request().postDataJSON();
    expect(body.expectedRevision).toBe(revision);
    claims = body.claims;
    revision += 1;
    await route.fulfill({
      json: {
        success: true,
        data: { claims, claimsRevision: revision },
        meta: { requestId: "claims-e2e" },
      },
    });
  });
  await page.goto(`/dossiers/${dossierId}`);
  await page.getByRole("button", { name: /2\. Tài liệu/ }).click();
  const editor = page.getByRole("region", { name: "Nhận định và căn cứ" });
  await editor.getByRole("button", { name: "Thêm nhận định" }).click();
  await editor
    .getByRole("textbox", { name: "Nội dung nhận định 1" })
    .fill("Bản thảo gốc ghi lại quá trình sáng tác độc lập của chủ thể.");
  await editor.getByRole("checkbox").first().check();
  await editor.getByRole("button", { name: "Lưu nhận định" }).click();
  await expect(editor.getByRole("status")).toHaveText("Nhận định đã lưu");
  expect(claims).toHaveLength(1);
  expect(claims[0]!.evidenceMediaIds).toHaveLength(1);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const accessibility = await new AxeBuilder({ page })
    .include("[aria-labelledby='dossier-claims-heading']")
    .analyze();
  expect(accessibility.violations.map(({ id }) => id)).toEqual([]);
  await page.screenshot({
    fullPage: true,
    path: info.outputPath("applicant-claim-evidence.png"),
  });
});
