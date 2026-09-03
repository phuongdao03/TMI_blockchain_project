import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context, request }) => {
  const reset = await request.post(
    "http://127.0.0.1:4010/api/e2e/reset-certificate-versions",
  );
  expect(reset.ok()).toBe(true);
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
  ]);
});

test("applicant sees a task-focused certificate history", async ({ page }) => {
  await page.goto("/certificates/7eaec2d2-c99a-42c9-8f1e-71462ba01ea0");

  await expect(
    page.getByRole("heading", { level: 1, name: "Bộ nhận diện TMI" }),
  ).toBeVisible();
  await expect(page.getByText("Lịch sử chứng thư")).toBeVisible();
  await expect(page.getByText("Đang có hiệu lực").first()).toBeVisible();
  await expect(page.getByText("Chưa có thay đổi cần cập nhật")).toBeVisible();
  await expect(
    page.getByText(/SUPER_ADMIN|database|schema|endpoint/i),
  ).toHaveCount(0);
  await expect(page.getByText("Mã toàn vẹn")).not.toBeVisible();

  await page.getByText("Xem thông tin đối chiếu nâng cao").click();
  await expect(page.getByText("Mã toàn vẹn")).toBeVisible();
});
