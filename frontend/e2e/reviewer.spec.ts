import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context, request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-review");
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
      name: "tmi_refresh",
      value: "e2e-refresh",
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
      httpOnly: false,
      sameSite: "Lax",
    },
    {
      // The mock API uses this non-sensitive test-only marker to return the
      // MODERATOR identity. Access tokens alone intentionally default to a
      // regular applicant, which would exercise the wrong dashboard.
      name: "tmi_e2e_persona",
      value: "reviewer",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
});

test("reviewer acknowledges conflict gate, reviews evidence and submits 5T", async ({
  page,
}, testInfo) => {
  const consoleIssues: string[] = [];
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleIssues.push(`${message.type()}: ${message.text()}`);
    }
  });

  await page.goto("/reviews");
  await expect(
    page
      .locator("main")
      .getByRole("heading", { level: 1, name: "Hàng đợi thẩm định" }),
  ).toBeVisible();
  const reviewLink = page.getByRole("link", { name: "Mở hồ sơ thẩm định" });
  await expect(reviewLink).toHaveAttribute(
    "href",
    /\/reviews\/4155dbf5-bb3e-449d-8bf0-9572cc642cac$/,
  );
  await page.goto("/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac");
  await expect(
    page.getByRole("heading", { level: 1, name: "Hồ sơ thương hiệu TMI" }),
  ).toBeVisible();
  await expect(page.getByText("Bằng chứng phiên bản đã khóa")).toHaveCount(0);

  await page.getByRole("button", { name: "Tôi không có xung đột" }).click();
  await expect(page.getByText("Bằng chứng phiên bản đã khóa")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Giấy xác nhận quyền sở hữu" }),
  ).toBeVisible();

  const evidencePreview = page.getByRole("region", { name: /xem tr/i });
  await page.locator('button[aria-label^="Xem "]').first().click();
  await expect(evidencePreview).toBeVisible();

  const criteria = [
    "Tính đúng đắn",
    "Tính minh bạch",
    "Quyền sở hữu & trách nhiệm",
    "Tính chuyên nghiệp",
    "Tính tôn trọng",
  ];
  for (const criterion of criteria) {
    await page.getByLabel(`Điểm ${criterion}`).fill("16");
    await page
      .getByLabel(`Nhận xét ${criterion}`)
      .fill(`Đánh giá E2E đầy đủ cho ${criterion}.`);
  }
  const checklist = page.getByRole("checkbox");
  const requiredChecklistCount = criteria.length + 4;
  await expect(checklist).toHaveCount(requiredChecklistCount);
  for (let index = 0; index < requiredChecklistCount; index += 1) {
    await checklist.nth(index).check();
  }
  const autosave = page.waitForResponse(
    (response) =>
      response.url().endsWith("/draft") &&
      response.request().method() === "PUT" &&
      response.status() === 200,
  );
  await page.getByLabel("Kiến nghị").selectOption("APPROVE");
  await autosave;

  await page.getByRole("button", { name: "Gửi kết quả thẩm định" }).click();
  await expect(
    page.getByRole("heading", { name: "Xác nhận gửi kết quả" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Xác nhận gửi" }).click();
  await expect(
    page.getByText("Kết quả đã gửi và không thể chỉnh sửa."),
  ).toBeVisible();

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
});

test("retired similarity route returns reviewer to the main queue", async ({
  page,
}) => {
  await page.goto("/reviews/similarity");
  await expect(page).toHaveURL(/\/reviews$/);
  await expect(
    page
      .locator("main")
      .getByRole("heading", { level: 1, name: "Hàng đợi thẩm định" }),
  ).toBeVisible();
});

test("reviewer assessment remains legible in dark mode", async ({ page }) => {
  await page.goto("/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac");
  await page.getByRole("button", { name: "Tôi không có xung đột" }).click();
  await page.getByRole("button", { name: "Giao diện tối" }).click();

  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(
    page.getByRole("heading", { name: "Phiếu thẩm định chuyên môn" }),
  ).toBeVisible();
  const firstCriterion = page
    .locator("fieldset")
    .filter({ hasText: "01" })
    .first();
  await expect(firstCriterion).not.toHaveCSS(
    "background-color",
    "rgba(0, 0, 0, 0)",
  );
  await expect(firstCriterion).toBeVisible();
});
