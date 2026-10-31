import { expect, test } from "@playwright/test";

import { selectWorkspaceTheme } from "./workspace-theme";
import { expectDocumentToFit } from "./responsive-layout";

const mockApiUrl = `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}`;

test.beforeEach(async ({ context, request }) => {
  await request.post(`${mockApiUrl}/api/e2e/reset-review`);
  await context.addCookies([
    {
      name: "cns_access",
      value: "e2e-access",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "cns_refresh",
      value: "e2e-refresh",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "cns_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
    {
      // The mock API uses this non-sensitive test-only marker to return the
      // MODERATOR identity. Access tokens alone intentionally default to a
      // regular applicant, which would exercise the wrong dashboard.
      name: "cns_e2e_persona",
      value: "reviewer",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
});

test("reviewer criteria and action bar fit every target viewport in both themes", async ({
  page,
}) => {
  await page.goto("/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac");
  await expect(
    page.getByRole("heading", { name: "Kết luận theo tiêu chí" }),
  ).toBeVisible();
  for (const theme of ["Giao diện sáng", "Giao diện tối"] as const) {
    await selectWorkspaceTheme(page, theme);
    for (const width of [320, 360, 375, 390, 414, 430, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      await expectDocumentToFit(page, `${theme} at ${width}px`);
      await expect(
        page.locator('fieldset[id^="review-criterion-"]:visible'),
      ).toHaveCount(1);
      if (width < 1024) {
        await page
          .getByRole("button", { name: "Gửi kết quả thẩm định" })
          .scrollIntoViewIfNeeded();
        const actions = await page.locator(".review-submit-bar").boundingBox();
        const navigation = await page
          .locator(".site-mobile-navigation")
          .boundingBox();
        expect(actions!.y + actions!.height).toBeLessThanOrEqual(
          navigation!.y + 1,
        );
      }
    }
  }
});

test("reviewer reviews each document and submits a criteria verdict", async ({
  page,
}, testInfo) => {
  const consoleIssues: string[] = [];
  page.on("console", (message) => {
    const expectedAuthProbe =
      message.type() === "error" &&
      message.text().includes("status of 401 (Unauthorized)");
    if (["error", "warning"].includes(message.type()) && !expectedAuthProbe) {
      consoleIssues.push(`${message.type()}: ${message.text()}`);
    }
  });

  await page.goto("/reviews", { waitUntil: "domcontentloaded" });
  await expect(
    page
      .locator("main")
      .getByRole("heading", { level: 1, name: "Công việc kiểm duyệt" }),
  ).toBeVisible();
  const reviewLink = page.getByRole("link", { name: "Tiếp tục thẩm định" });
  await expect(reviewLink).toHaveAttribute(
    "href",
    /\/reviews\/4155dbf5-bb3e-449d-8bf0-9572cc642cac$/,
  );
  await page.goto("/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac", {
    waitUntil: "domcontentloaded",
  });
  await expect(
    page.getByRole("heading", { level: 1, name: "Hồ sơ thương hiệu THV" }),
  ).toBeVisible();
  await expect(page.getByText("Bằng chứng phiên bản đã khóa")).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Bằng chứng về quyền sử dụng nhãn hiệu",
    }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Loại tài liệu: Tài liệu về quyền sử dụng hoặc đại diện nhãn hiệu",
    ),
  ).toBeVisible();
  await expect(page.getByText("Định dạng: PDF")).toBeVisible();
  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("review-form-before-submit.png"),
  });

  const evidencePreview = page.getByRole("region", { name: /xem tr/i });
  await page.locator('button[aria-label^="Xem "]').first().click();
  await expect(evidencePreview).toBeVisible();

  await page
    .getByLabel("Kết quả kiểm tra Bằng chứng về quyền sử dụng nhãn hiệu")
    .selectOption("VALID");
  const criteria = [
    "Căn cứ quyền sử dụng nhãn hiệu",
    "Thông tin nhất quán",
    "Đủ căn cứ xác minh",
  ];
  await expect(
    page.locator('fieldset[id^="review-criterion-"]:visible'),
  ).toHaveCount(1);
  for (const criterion of criteria) {
    await page
      .getByRole("navigation", { name: "Tiến độ từng tiêu chí" })
      .getByRole("button", { name: new RegExp(criterion) })
      .click();
    const meetsCriterion = page.getByRole("radio", {
      name: `${criterion}: Đáp ứng`,
    });
    await meetsCriterion.focus();
    await meetsCriterion.press("Space");
    await expect(meetsCriterion).toBeChecked();
    await page
      .getByLabel(`Nhận định ${criterion}`)
      .fill(`Đã đối chiếu tài liệu và xác nhận ${criterion.toLowerCase()}.`);
    await page
      .locator('fieldset[id^="review-criterion-"]:visible')
      .getByRole("checkbox")
      .check();
  }
  await page
    .getByRole("navigation", { name: "Tiến độ từng tiêu chí" })
    .getByRole("button", { name: new RegExp(criteria[0]!) })
    .click();
  await expect(page.getByLabel(`Nhận định ${criteria[0]}`)).toHaveValue(
    `Đã đối chiếu tài liệu và xác nhận ${criteria[0]!.toLowerCase()}.`,
  );
  await expect(
    page
      .locator('fieldset[id^="review-criterion-"]:visible')
      .getByRole("checkbox"),
  ).toBeChecked();
  await expect(
    page.locator("#review-final-result").getByText("Đề nghị phê duyệt"),
  ).toBeVisible();
  await expect(page.getByText("0/100")).toHaveCount(0);

  await page.getByRole("button", { name: "Gửi kết quả thẩm định" }).click();
  await expect(
    page.getByRole("heading", { name: "Xác nhận gửi kết quả" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Xác nhận gửi" }).click();
  await expect(page.getByText("Kết quả đã gửi.")).toBeVisible();

  const overflow = await page.evaluate(() => {
    const width = document.documentElement.clientWidth;
    return Array.from(document.querySelectorAll<HTMLElement>("body *"))
      .map((element) => ({
        right: Math.round(element.getBoundingClientRect().right),
        tag: element.tagName,
      }))
      .filter(({ right }) => right > width + 1)
      .slice(0, 8);
  });
  expect(overflow).toEqual([]);
  await page.screenshot({
    fullPage: false,
    path: testInfo.outputPath("review-submitted.png"),
  });
  expect(consoleIssues).toEqual([]);

  await page.context().addCookies([
    {
      name: "cns_e2e_persona",
      value: "super-admin",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);
  await page.goto("/admin/reviews/9155dbf5-bb3e-449d-8bf0-9572cc642cac", {
    waitUntil: "domcontentloaded",
  });
  await expect(
    page.getByRole("heading", { name: "Báo cáo kiểm duyệt" }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Nhận định theo từng tiêu chí" }),
  ).toContainText(
    "Đã đối chiếu tài liệu và xác nhận căn cứ quyền sử dụng nhãn hiệu",
  );
  await expect(
    page.getByRole("region", { name: "Nhận định theo từng tiêu chí" }),
  ).toContainText("Bằng chứng về quyền sử dụng nhãn hiệu");
  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("admin-review-report.png"),
  });
});

test("retired similarity route returns reviewer to the main queue", async ({
  page,
}) => {
  await page.goto("/reviews/similarity", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/reviews$/);
  await expect(
    page
      .locator("main")
      .getByRole("heading", { level: 1, name: "Công việc kiểm duyệt" }),
  ).toBeVisible();
});

test("reviewer form fits tablet width", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 820, height: 1180 });
  await page.goto("/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac", {
    waitUntil: "domcontentloaded",
  });
  await expect(
    page.getByRole("heading", { name: "Kết luận theo tiêu chí" }),
  ).toBeVisible();
  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth,
  );
  expect(overflow).toBe(false);
  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("review-form-tablet.png"),
  });
});

test("reviewer assessment remains legible in dark mode", async ({
  page,
}, testInfo) => {
  test.setTimeout(120_000);
  await page.goto("/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac", {
    waitUntil: "domcontentloaded",
  });
  await selectWorkspaceTheme(page, "Giao diện tối");

  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const reviewHeader = page.locator(".review-workspace > section > header");
  await expect(reviewHeader).toHaveCSS("color", "rgb(255, 249, 243)");
  await expect(
    page.getByRole("heading", { name: "Kết luận theo tiêu chí" }),
  ).toBeVisible();
  const firstCriterion = page
    .locator("fieldset")
    .filter({ hasText: "01" })
    .first();
  await expect(firstCriterion).toBeVisible();
  await expect(firstCriterion).not.toHaveCSS(
    "background-color",
    "rgb(255, 255, 255)",
  );
  await expect(firstCriterion).toHaveCSS("color", "rgb(255, 249, 243)");
  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("review-form-dark.png"),
  });

  await selectWorkspaceTheme(page, "Giao diện sáng");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(reviewHeader).toHaveCSS("color", "rgb(36, 21, 21)");
});
