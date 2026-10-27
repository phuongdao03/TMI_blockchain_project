import { expect, test } from "@playwright/test";

import { selectWorkspaceTheme } from "./workspace-theme";

const mockApiUrl = `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}`;

const baseCookies = [
  ["cns_access", "e2e-access", true],
  ["cns_refresh", "e2e-refresh", true],
  ["cns_csrf", "e2e-csrf", false],
] as const;

test.beforeEach(async ({ context, request }) => {
  await request.post(
    `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}/api/e2e/reset-preparation`,
  );
  await context.addCookies(
    baseCookies.map(([name, value, httpOnly]) => ({
      name,
      value,
      domain: "127.0.0.1",
      path: "/",
      httpOnly,
      sameSite: "Lax" as const,
    })),
  );
});

test("applicant sees a server-driven preparation journey", async ({ page }) => {
  await page.goto("/dossiers/new");
  await page.locator(".dossier-type-option").first().click();

  await expect(
    page.getByRole("navigation", { name: "Các bước chuẩn bị hồ sơ nháp" }),
  ).toBeVisible();
  const preparation = page.locator(".dossier-preflight");
  await expect(
    preparation.getByRole("heading", {
      name: "Khác biệt của loại hồ sơ này",
    }),
  ).toBeVisible();
  await expect(
    preparation.getByRole("heading", { name: "Thông tin cần khai" }),
  ).toBeVisible();
  await expect(preparation.getByText("Giấy tờ bắt buộc:")).toBeVisible();
  await selectWorkspaceTheme(page, "Giao diện tối");
  await expect(preparation).not.toHaveCSS(
    "background-color",
    "rgb(255, 255, 255)",
  );
  await expect(page.locator("body")).not.toHaveCSS("overflow-x", "scroll");
});

test("mobile applicant journey is compact without page overflow", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chrome");
  await page.goto("/dossiers/new");

  const journey = page.locator(".dossier-journey");
  await expect(journey).toBeVisible();
  await expect(journey).toHaveCSS("display", "grid");
  await expect(journey).toHaveClass(/dossier-journey--three/);
  expect(
    await journey.evaluate(
      (element) =>
        getComputedStyle(element).gridTemplateColumns.split(" ").length,
    ),
  ).toBe(2);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("reviewer sees live progress and the next blocking action", async ({
  context,
  page,
  request,
}) => {
  await request.post(`${mockApiUrl}/api/e2e/reset-review`);
  await context.addCookies([
    {
      name: "cns_e2e_persona",
      value: "reviewer",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
  await page.goto("/reviews", { waitUntil: "domcontentloaded" });
  await page.getByRole("link", { name: "Tiếp tục thẩm định" }).click();
  await expect(page.getByText("Đã quá hạn xử lý")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Tài liệu kiểm chứng (1)" }),
  ).toBeVisible();
  await expect(page.getByText("Tóm tắt của người nộp")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Phiếu thẩm định" }),
  ).toHaveAttribute("href", "#review-scorecard");
  await expect(
    page.getByRole("status").filter({ hasText: "Tiếp theo:" }),
  ).toBeVisible();
  const reviewLayout = await page
    .locator("#review-form")
    .evaluate((element) => {
      const evidence = element
        .querySelector("#review-evidence")!
        .getBoundingClientRect();
      const scorecard = element
        .querySelector("#review-scorecard")!
        .getBoundingClientRect();
      return {
        evidenceBottom: evidence.bottom,
        evidenceWidth: evidence.width,
        scorecardTop: scorecard.top,
        scorecardWidth: scorecard.width,
      };
    });
  expect(reviewLayout.scorecardTop).toBeGreaterThanOrEqual(
    reviewLayout.evidenceBottom - 2,
  );
  expect(reviewLayout.scorecardWidth).toBeGreaterThanOrEqual(
    reviewLayout.evidenceWidth * 0.95,
  );
  await page
    .getByRole("button", { name: "Xem Bằng chứng về quyền sử dụng nhãn hiệu" })
    .click();
  await expect(
    page.getByRole("region", {
      name: "Xem trước Bằng chứng về quyền sử dụng nhãn hiệu",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Kết luận theo tiêu chí" }),
  ).toBeVisible();
  await expect(page.getByText("Kết luận từng tiêu chí")).toBeVisible();
  await expect(page.getByText("0/5 tiêu chí hoàn tất")).toHaveCount(0);
  await expect(
    page.getByText(
      "Loại tài liệu: Tài liệu về quyền sử dụng hoặc đại diện nhãn hiệu",
    ),
  ).toBeVisible();
});
