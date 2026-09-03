import { expect, test } from "@playwright/test";

test("super admin reviews and safely replays failed background work", async ({
  context,
  page,
  request,
}) => {
  test.setTimeout(60_000);
  await request.post("http://127.0.0.1:4010/api/e2e/reset-operations-job");
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
