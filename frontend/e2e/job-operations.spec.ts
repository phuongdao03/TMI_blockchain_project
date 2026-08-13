import { expect, test } from "@playwright/test";

test("super admin reviews and safely replays failed background work", async ({
  page,
}) => {
  await page.goto("/login");
  await page
    .getByRole("textbox", { name: "Email" })
    .fill("superadmin@tmigroup.vn");
  await page.getByLabel(/Mật khẩu/i).fill("correct horse battery staple");
  await page.getByRole("button", { name: "Đăng nhập" }).click();

  await expect(page).toHaveURL(/\/admin(?:\/dashboard)?$/);
  await page.goto("/admin/dashboard");

  await expect(
    page.getByRole("heading", { name: "Công việc nền gần đây" }),
  ).toBeVisible();
  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(
      page.getByRole("heading", { name: "Công việc nền gần đây" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  await expect(page.getByText("Phát hành chứng thư")).toBeVisible();
  await expect(page.getByText("blockchain.broadcast")).toBeHidden();

  await page.getByText("Xem chi tiết").click();
  await expect(page.getByText("blockchain.broadcast")).toBeVisible();
  await page.getByRole("button", { name: "Thử lại" }).click();

  const confirm = page.getByRole("button", { name: "Xác nhận thử lại" });
  await expect(confirm).toBeDisabled();
  await page
    .getByLabel("Lý do xử lý")
    .fill("Kết nối nhà cung cấp đã hoạt động ổn định");
  await confirm.click();

  await expect(page.getByText("Đang chờ", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Hủy công việc" }),
  ).toBeVisible();
});
