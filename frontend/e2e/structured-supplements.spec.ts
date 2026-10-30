import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { SupplementRequest } from "../src/lib/api/supplements";

const dossierId = "9155dbf5-bb3e-449d-8bf0-9572cc642cac";
const versionId = "8155dbf5-bb3e-449d-8bf0-9572cc642cac";
test("criterion request reaches owner response and staff resolution with history", async ({
  context,
  page,
  request,
}, info) => {
  await request.post(
    `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}/api/e2e/reset-review`,
  );
  const setRole = (role: string) =>
    context.addCookies(
      [
        ["cns_access", "e2e-access"],
        ["cns_refresh", "e2e-refresh"],
        ["cns_csrf", "e2e-csrf"],
        ["cns_e2e_persona", role],
      ].map(([name, value]) => ({
        name: name!,
        value: value!,
        domain: "127.0.0.1",
        path: "/",
        sameSite: "Lax" as const,
      })),
    );
  await setRole("reviewer");
  const envelope = (data: unknown) => ({
    success: true,
    data,
    meta: { requestId: "supplement-e2e" },
  });
  const requests: SupplementRequest[] = [];
  await page.route(
    `**/api/v1/dossiers/${dossierId}/supplement-requests**`,
    async (route) => {
      const method = route.request().method();
      const path = new URL(route.request().url()).pathname;
      if (method === "GET") return route.fulfill({ json: envelope(requests) });
      const body = route.request().postDataJSON();
      if (path.endsWith("/response") || path.endsWith("/resolve")) {
        const item = requests[0]!;
        expect(body.expectedRevision).toBe(item.revision);
        item.revision += 1;
        const owner = path.endsWith("/response");
        item.status = owner ? "ANSWERED" : "RESOLVED";
        item.responses.push({
          id: `entry-${item.revision}`,
          sequenceNo: item.revision,
          kind: owner ? "RESPONSE" : "RESOLVE",
          text: owner ? body.text : body.resolution,
          createdAt: "2026-10-30T00:00:00Z",
        });
        return route.fulfill({ json: envelope(item) });
      }
      expect(body.expectedVersionId).toBe(versionId);
      const item: SupplementRequest = {
        id: "a155dbf5-bb3e-449d-8bf0-9572cc642cac",
        dossierId,
        requestedVersionId: versionId,
        criterionKey: body.criterionKey,
        criterionLabel: "Căn cứ quyền sử dụng nhãn hiệu",
        claimId: null,
        requestedInformation: body.requestedInformation,
        reason: body.reason,
        priority: body.priority,
        dueAt: body.dueAt,
        createdAt: "2026-10-30T00:00:00Z",
        status: "OPEN",
        revision: 0,
        responses: [],
      };
      requests.push(item);
      return route.fulfill({ status: 201, json: envelope(item) });
    },
  );
  const reviewerPath = "/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac";
  await page.goto(reviewerPath);
  let panel = page.getByRole("region", { name: "Yêu cầu bổ sung có cấu trúc" });
  await panel.getByText("Tạo yêu cầu bổ sung theo tiêu chí").click();
  await panel
    .getByLabel("Tiêu chí cần bổ sung")
    .selectOption("ownership_basis");
  const requirement =
    "Bổ sung tư liệu có niên đại xác định chủ thể được khai báo.";
  await panel.getByLabel("Thông tin cần bổ sung").fill(requirement);
  await panel
    .getByLabel("Lý do cần bổ sung")
    .fill("Nguồn hiện có chưa thể đối chiếu đầy đủ chủ thể và niên đại.");
  await panel.getByRole("button", { name: "Lưu yêu cầu bổ sung" }).click();
  await expect(panel.getByText(requirement)).toBeVisible();
  await page.route(`**/api/v1/dossiers/${dossierId}`, (route) =>
    route.fulfill({
      json: envelope({
        id: dossierId,
        code: "THV-SUPPLEMENT-TEST",
        ownerUserId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
        organizationId: null,
        categoryId: "4d28db19-1507-5a45-a50d-cd0aa83029ec",
        dossierTypeId: null,
        dossierTypeVersionId: null,
        formData: {},
        title: "Hồ sơ cần làm rõ nguồn gốc",
        summary: "Tư liệu đang được bổ sung",
        slug: null,
        status: "NEEDS_SUPPLEMENT",
        visibility: "PRIVATE",
        currentVersionNo: 1,
        submittedAt: "2026-10-30T00:00:00Z",
        createdAt: "2026-10-30T00:00:00Z",
        updatedAt: "2026-10-30T00:00:00Z",
        canEdit: true,
        evidences: [],
        documentRules: [],
        claims: [],
        claimsRevision: 0,
        claimCriteria: [],
      }),
    }),
  );
  await setRole("applicant");
  await page.goto(`/dossiers/${dossierId}`);
  panel = page.getByRole("region", { name: "Yêu cầu bổ sung có cấu trúc" });
  await expect(panel.getByText(requirement)).toBeVisible();
  const reply =
    "Đã bổ sung hồ sơ lưu trữ có niên đại và bản giải trình chủ thể.";
  await panel.getByLabel("Nội dung xử lý yêu cầu 1").fill(reply);
  await panel.getByRole("button", { name: "Gửi phản hồi" }).click();
  await expect(panel.getByText("Đã phản hồi, chờ kiểm tra")).toBeVisible();
  await setRole("reviewer");
  await page.goto(reviewerPath);
  panel = page.getByRole("region", { name: "Yêu cầu bổ sung có cấu trúc" });
  const resolution =
    "Đã đối chiếu tư liệu và giải trình; yêu cầu đã được xử lý.";
  await panel.getByLabel("Nội dung xử lý yêu cầu 1").fill(resolution);
  await panel.getByRole("button", { name: "Xác nhận đã xử lý" }).click();
  await expect(panel.getByText("Đã xử lý", { exact: true })).toBeVisible();
  await expect(panel.getByText(reply)).toBeVisible();
  await expect(panel.getByText(resolution)).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const audit = await new AxeBuilder({ page })
    .include("[aria-label='Yêu cầu bổ sung có cấu trúc']")
    .analyze();
  expect(audit.violations.map(({ id }) => id)).toEqual([]);
  await page.screenshot({
    fullPage: true,
    path: info.outputPath("structured-supplements.png"),
  });
});
