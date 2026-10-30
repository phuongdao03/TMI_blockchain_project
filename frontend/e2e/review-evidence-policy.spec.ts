import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const mockApiUrl = `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}`;

test("reviewer distinguishes relevance, incomplete verification and contradiction", async ({
  context,
  page,
  request,
}, info) => {
  await request.post(`${mockApiUrl}/api/e2e/reset-review`);
  await context.addCookies(
    [
      ["cns_access", "e2e-access"],
      ["cns_refresh", "e2e-refresh"],
      ["cns_csrf", "e2e-csrf"],
      ["cns_e2e_persona", "reviewer"],
    ].map(([name, value]) => ({
      name: name!,
      value: value!,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax" as const,
    })),
  );
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route(
    "**/api/v1/reviewer/assignments/4155dbf5-bb3e-449d-8bf0-9572cc642cac",
    async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      const rubric = json.data.snapshotJson.dossier.dossierType.reviewRubric;
      rubric.evidencePolicyVersion = "2026.1";
      rubric.criteria.forEach((criterion: Record<string, unknown>) => {
        criterion.allowNotApplicable = false;
        criterion.verificationRequired = true;
      });
      await route.fulfill({ response, json });
    },
  );
  await page.goto("/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac");
  const title = "Bằng chứng về quyền sử dụng nhãn hiệu";
  const verification = page.getByLabel(`Kiểm chứng nội dung ${title}`);
  await expect(verification).toHaveValue("UNVERIFIED");
  await page.getByLabel(`Kết quả kiểm tra ${title}`).selectOption("VALID");
  const meets = page.getByRole("radio", {
    name: "Căn cứ quyền sử dụng nhãn hiệu: Đáp ứng",
    exact: true,
  });
  await meets.focus();
  await meets.press("Space");
  await expect(meets).toBeChecked();
  await expect(
    page.getByRole("radio", { name: /: Không áp dụng/ }),
  ).toHaveCount(0);
  await verification.selectOption("PARTIAL");
  await page.getByRole("button", { name: "Gửi kết quả thẩm định" }).click();
  await expect(
    page.locator("#review-scorecard").getByRole("alert"),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Xác nhận gửi" })).toHaveCount(
    0,
  );
  for (const [label, value] of [
    ["Phương pháp đối chiếu", "So sánh với hồ sơ lưu trữ gốc"],
    ["Nguồn đối chiếu", "Kho lưu trữ, mục 2024, trang 3"],
    ["Phạm vi đã kiểm tra", "Chủ thể và ngày sáng tác"],
    ["Giới hạn kiểm chứng", "Chỉ đối chiếu nguồn được cung cấp"],
  ])
    await page
      .getByRole("textbox", { name: `${label} — ${title}` })
      .fill(value!);
  await page
    .getByLabel("Nhận định Căn cứ quyền sử dụng nhãn hiệu")
    .fill("Đã đối chiếu chủ thể và thời điểm với nguồn lưu trữ được cung cấp.");
  await page
    .locator("#review-criterion-ownership_basis")
    .getByRole("checkbox")
    .check();
  await verification.selectOption("CONTRADICTED");
  await expect(
    page.getByText(/minh chứng còn thiếu căn cứ hoặc mâu thuẫn/).first(),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const accessibility = await new AxeBuilder({ page })
    .include("#review-scorecard")
    .analyze();
  expect(accessibility.violations.map(({ id }) => id)).toEqual([]);
  expect(errors).toEqual([]);
  await page.screenshot({
    fullPage: true,
    path: info.outputPath("evidence-policy-review.png"),
  });
});
