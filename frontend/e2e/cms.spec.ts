import { expect, test } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-cms");
});

test("content admin creates, previews and publishes a sanitized post", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Email" }).fill("owner@tmigroup.vn");
  await page
    .getByLabel(/Mật khẩu|Máº­t kháº©u/)
    .fill("correct horse battery staple");
  await page.getByRole("button", { name: /Đăng nhập|ÄÄƒng nháº­p/ }).click();

  await expect(page).toHaveURL(/\/admin\/content$/);
  await page.locator("nav").getByRole("button").nth(1).click();
  await expect(
    page.getByRole("heading", { name: "Trung tâm nội dung" }),
  ).toBeVisible();

  await page.getByLabel("Tiêu đề").fill("Thông báo xác lập");
  await page.getByLabel("Slug").fill("thong-bao-xac-lap");
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
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Email" }).fill("owner@tmigroup.vn");
  await page.getByLabel(/khẩu/i).fill("correct horse battery staple");
  await page.getByRole("button", { name: /Đăng nhập/i }).click();

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
