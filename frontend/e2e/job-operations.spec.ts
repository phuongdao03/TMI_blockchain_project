import { expect, test } from "@playwright/test";

const mockApiUrl = `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}`;

test("super admin reviews and safely replays failed background work", async ({
  context,
  page,
  request,
}) => {
  test.setTimeout(60_000);
  await request.post(`${mockApiUrl}/api/e2e/reset-operations-job`);
  await context.addCookies([
    {
      name: "cns_access",
      value: "e2e-super-admin-access",
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
    await expect
      .poll(
        () =>
          page.evaluate(() => {
            const viewport = window.innerWidth;
            const documentWidth = document.documentElement.scrollWidth;
            const offenders = Array.from(document.body.querySelectorAll("*"))
              .map((element) => {
                const rect = element.getBoundingClientRect();
                return {
                  tag: element.tagName.toLowerCase(),
                  className:
                    typeof element.className === "string"
                      ? element.className.slice(0, 100)
                      : "",
                  right: Math.round(rect.right),
                  width: Math.round(rect.width),
                };
              })
              .filter((item) => item.width > 0 && item.right > viewport + 1)
              .slice(0, 8);
            return {
              fits: documentWidth <= viewport,
              viewport,
              documentWidth,
              offenders,
            };
          }),
        { message: "Background work page should fit at each viewport" },
      )
      .toMatchObject({ fits: true });
  }
  await expect(page.getByText("Phát hành bằng xác lập")).toBeVisible();
  await expect(page.getByText("blockchain.broadcast")).toHaveCount(0);
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
