import { expect, test } from "@playwright/test";

const baseCookies = [
  ["tmi_access", "e2e-access", true],
  ["tmi_refresh", "e2e-refresh", true],
  ["tmi_csrf", "e2e-csrf", false],
] as const;

test.beforeEach(async ({ context }) => {
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
    page.getByRole("navigation", { name: "Các bước gửi hồ sơ" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Tài liệu cần chuẩn bị" }),
  ).toBeVisible();
  await expect(page.getByText(/tệp được tải lên sau khi bản nháp/i)).toBeVisible();
  await page.getByRole("button", { name: "Giao diện tối" }).click();
  const preparation = page.getByRole("heading", {
    name: "Tài liệu cần chuẩn bị",
  }).locator("..", { hasText: "Tệp được tải lên" });
  await expect(preparation).not.toHaveCSS("background-color", "rgb(255, 255, 255)");
  await expect(page.locator("body")).not.toHaveCSS("overflow-x", "scroll");
});

test("mobile applicant journey is compact without page overflow", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chrome");
  await page.goto("/dossiers/new");

  const journey = page.locator(".dossier-journey");
  await expect(journey).toBeVisible();
  await expect(journey).toHaveCSS("overflow-x", "auto");
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
  await request.post("http://127.0.0.1:4010/api/e2e/reset-review");
  await context.addCookies([
    {
      name: "tmi_e2e_persona",
      value: "reviewer",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
  await page.goto("/reviews");
  await page.getByRole("link", { name: "Mở hồ sơ thẩm định" }).click();
  await page.getByRole("button", { name: "Tôi không có xung đột" }).click();

  await expect(page.getByText("Đã quá SLA")).toBeVisible();
  await expect(page.getByText("1 tài liệu đã khóa")).toBeVisible();
  await expect(page.getByText("Tóm tắt của người nộp")).toBeVisible();
  await page
    .getByRole("button", { name: "Xem Giấy xác nhận quyền sở hữu" })
    .click();
  await expect(
    page.getByRole("region", {
      name: "Xem trước Giấy xác nhận quyền sở hữu",
    }),
  ).toBeVisible();
  await expect(page.getByText("0/5 tiêu chí hoàn tất")).toBeVisible();
  await expect(
    page.getByText(/Tiếp theo: Chấm điểm và nhận xét tiêu chí/),
  ).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Đi tới phần của phiếu" }),
  ).toBeVisible();
});
