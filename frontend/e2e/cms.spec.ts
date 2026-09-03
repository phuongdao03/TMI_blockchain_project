import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context, request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-cms");
  await context.addCookies([
    {
      name: "tmi_access",
      value: "e2e-super-admin-access",
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
      sameSite: "Lax",
    },
  ]);
});

test("content admin creates, previews and publishes a sanitized post", async ({
  page,
}) => {
  test.setTimeout(90_000);
  await page.goto("/admin/content");
  await page.getByRole("button", { name: "Bài viết" }).click();
  await expect(
    page.getByRole("heading", { name: "Trung tâm nội dung" }),
  ).toBeVisible();

  await page.getByLabel("Tiêu đề").fill("Thông báo xác lập");
  await page.getByLabel("Đường dẫn công khai").fill("thong-bao-xac-lap");
  await page
    .getByLabel("Nội dung HTML giới hạn")
    .fill("<p>Nội dung đã duyệt</p>");
  await page.getByRole("button", { name: "Lưu bản nháp" }).click();

  await expect(page.getByText("Thông báo xác lập")).toBeVisible();
  await page.getByRole("button", { name: "Xem trước" }).click();
  await expect(page.getByText("Nội dung đã duyệt")).toBeVisible();
  await page.getByRole("button", { name: "Xuất bản" }).click();
  await expect(page.getByText("PUBLISHED")).toBeVisible();
});

test("content admin previews and publishes a public work", async ({ page }) => {
  await page.goto("/admin/content");
  await page.getByRole("button", { name: /Di sản số TMI/ }).click();
  await expect(page.getByLabel("Tiêu đề công khai")).toHaveValue(
    "Di sản số TMI",
  );
  await page.getByRole("button", { name: "Xem trước" }).click();
  await expect(page.getByText(/Tác phẩm số đã hoàn tất/)).toBeVisible();
  await page.getByRole("button", { name: "Đóng xem trước" }).click();
  await page.getByRole("button", { name: "Xuất bản" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Xuất bản" })
    .click();
  await expect(page.getByRole("button", { name: "Ẩn tác phẩm" })).toBeVisible();
});
