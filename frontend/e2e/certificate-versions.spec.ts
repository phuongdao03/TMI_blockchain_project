import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context, request }) => {
  const reset = await request.post(
    `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}/api/e2e/reset-certificate-versions`,
  );
  expect(reset.ok()).toBe(true);
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
  ]);
});

test("applicant sees a task-focused certificate history", async ({ page }) => {
  await page.goto("/certificates/7eaec2d2-c99a-42c9-8f1e-71462ba01ea0");

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Video chào mừng thương hiệu Đề cử Tinh Hoa Việt",
    }),
  ).toBeVisible();
  const viewer = page.getByRole("region", { name: "Bằng xác lập PDF" });
  await expect(viewer).toBeVisible();
  const pdfPage = viewer.getByRole("img", {
    name: "Trang 1 của bằng xác lập PDF",
  });
  await expect(pdfPage).toBeVisible();
  await expect
    .poll(() => pdfPage.evaluate((canvas: HTMLCanvasElement) => canvas.width))
    .toBeGreaterThan(0);
  const originalWidth = await pdfPage.evaluate(
    (canvas: HTMLCanvasElement) => canvas.width,
  );
  const originalHeight = await pdfPage.evaluate(
    (canvas: HTMLCanvasElement) => canvas.height,
  );
  expect(originalWidth).toBeGreaterThan(originalHeight);
  await viewer.getByRole("button", { name: "Phóng to PDF" }).click();
  await expect(viewer.getByRole("button", { name: "Vừa khung" })).toHaveText(
    "125%",
  );
  await expect
    .poll(() => pdfPage.evaluate((canvas: HTMLCanvasElement) => canvas.width))
    .toBeGreaterThan(originalWidth);
  await viewer.getByRole("button", { name: "Vừa khung" }).click();
  await expect(
    viewer.getByRole("button", { name: "Mở PDF trong thẻ mới" }),
  ).toBeEnabled();
  const [pdfTab] = await Promise.all([
    page.waitForEvent("popup"),
    viewer.getByRole("button", { name: "Mở PDF trong thẻ mới" }).click(),
  ]);
  await expect(pdfTab).toHaveURL(
    /\/api\/v1\/certificates\/[^/]+\/pdf\?inline=1$/,
  );
  await pdfTab.close();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
  await expect(page.getByText("Lịch sử bằng xác lập")).toBeVisible();
  await expect(page.getByText("Đang có hiệu lực").first()).toBeVisible();
  await expect(page.getByText("Chưa có thay đổi cần cập nhật")).toBeVisible();
  await expect(
    page.getByText(/SUPER_ADMIN|database|schema|endpoint/i),
  ).toHaveCount(0);
  await expect(
    page.getByText("Mã toàn vẹn", { exact: true }),
  ).not.toBeVisible();
  await expect(page.getByAltText("Mã QR kiểm tra bằng xác lập")).toBeVisible();

  await page.getByText("Xem thông tin đối chiếu nâng cao").click();
  await expect(page.getByText("Mã toàn vẹn", { exact: true })).toBeVisible();
});
