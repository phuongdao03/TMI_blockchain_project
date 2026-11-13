import { expect, test } from "@playwright/test";

test("TEST applicant skips the fee without starting a payment", async ({
  context,
  page,
}) => {
  const id = "9155dbf5-bb3e-449d-8bf0-9572cc642cac";
  const now = "2026-11-13T08:00:00Z";
  const evidence = {
    id: "evidence-1",
    dossierId: id,
    dossierVersionId: null,
    mediaAssetId: "media-1",
    evidenceType: "OWNERSHIP_DOCUMENT",
    evidenceRole: "OWNERSHIP_DOCUMENT",
    accessScope: "INTERNAL",
    title: "Bằng chứng quyền sở hữu",
    filename: "proof.pdf",
    description: null,
    issuedAt: null,
    displayOrder: 0,
    isPublic: false,
    mimeType: "application/pdf",
    bytes: 2048,
    sha256: "a".repeat(64),
  };
  const dossier = {
    id,
    code: "THV-2026-TEST",
    ownerUserId: "e57912cc-714c-4ab5-9fd9-1c5b38cd902b",
    organizationId: null,
    categoryId: "category-1",
    dossierTypeId: "type-1",
    dossierTypeVersionId: "type-version-1",
    formData: {},
    title: "Hồ sơ tài khoản kiểm thử",
    slug: null,
    summary: "Hồ sơ E2E TEST",
    status: "DRAFT",
    visibility: "PRIVATE",
    currentVersionNo: 0,
    submittedAt: null,
    createdAt: now,
    updatedAt: now,
    canEdit: true,
    claims: [],
    evidences: [evidence],
    documentRules: [
      {
        key: "OWNERSHIP_DOCUMENT",
        label: "Tài liệu quyền sở hữu",
        documentType: "OWNERSHIP_DOCUMENT",
        required: true,
        allowedMimeTypes: ["application/pdf"],
        maxBytes: 31_457_280,
        maxCount: 1,
        defaultVisibility: "INTERNAL",
      },
    ],
  };
  const envelope = (data: unknown) => ({
    success: true,
    data,
    meta: { request_id: "test-account-submission" },
  });
  await context.addCookies(
    (
      [
        ["cns_access", "e2e-access"],
        ["cns_refresh", "e2e-refresh"],
        ["cns_csrf", "e2e-csrf"],
        ["cns_e2e_persona", "test-applicant"],
      ] as const
    ).map(([name, value]) => ({
      name,
      value,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax" as const,
    })),
  );

  await page.route(`**/api/v1/dossiers/${id}`, (route) =>
    route.fulfill({ json: envelope(dossier) }),
  );
  await page.route(`**/api/v1/dossiers/${id}/versions`, (route) =>
    route.fulfill({ json: envelope([]) }),
  );
  await page.route(`**/api/v1/dossiers/${id}/timeline`, (route) =>
    route.fulfill({ json: envelope([]) }),
  );
  await page.route(`**/api/v1/dossiers/${id}/submission-fee`, (route) =>
    route.fulfill({
      json: envelope({
        feeRequired: true,
        feeAvailable: true,
        amountMinor: 5_000_000,
        currency: "VND",
        policyId: "policy-1",
        policyVersionNo: 1,
        description: "Phí hồ sơ thử nghiệm",
      }),
    }),
  );
  let paymentRequests = 0;
  page.on("request", (request) => {
    if (
      /\/api\/v1\/(?:payment-orders|payments|dossiers\/[^/]+\/submission-payment)/.test(
        request.url(),
      )
    ) {
      paymentRequests += 1;
    }
  });
  await page.route(`**/api/v1/dossiers/${id}/submit`, async (route) => {
    expect(route.request().headers()["x-test-payment-mode"]).toBe("SKIP");
    expect(route.request().headers()["x-fee-policy-version"]).toBeUndefined();
    await route.fulfill({
      json: envelope({
        dossier: { ...dossier, status: "SUBMITTED", canEdit: false },
        version: { id: "version-test", submittedAt: now },
      }),
    });
  });

  await page.goto(`/dossiers/${id}`);
  await expect(
    page.getByRole("heading", { level: 1, name: dossier.title }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Kiểm tra & nộp/ }).click();
  const mode = page.getByRole("combobox", { name: "Chế độ kiểm thử" });
  await expect(mode).toHaveValue("SKIP");
  await expect(
    page.getByText(/không trừ ví, không gọi cổng thanh toán thật/),
  ).toBeVisible();
  const submitButton = page.getByRole("button", { name: "Nộp hồ sơ" });
  await submitButton.evaluate((button) =>
    button.scrollIntoView({ block: "center" }),
  );
  await submitButton.evaluate((button) => {
    const navigation = document.querySelector(".site-mobile-navigation");
    const scrollport = document.scrollingElement;
    if (!navigation || !scrollport) return;

    const safeBottom = navigation.getBoundingClientRect().top - 16;
    const overlap = button.getBoundingClientRect().bottom - safeBottom;
    if (overlap <= 0) return;

    const previousScrollBehavior = scrollport.style.scrollBehavior;
    scrollport.style.scrollBehavior = "auto";
    scrollport.scrollTop += overlap;
    scrollport.style.scrollBehavior = previousScrollBehavior;
  });
  await submitButton.click();
  await expect(page.getByText("Hồ sơ đã được gửi thành công")).toBeVisible();
  expect(paymentRequests).toBe(0);
});
