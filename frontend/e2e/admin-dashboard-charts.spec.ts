import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context }) => {
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

test("admin charts stay readable and refresh on desktop and mobile", async ({
  page,
}) => {
  await page.goto("/admin/dashboard");

  await expect(
    page.getByRole("img", { name: "Biểu đồ số hồ sơ theo giai đoạn" }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: "Biểu đồ cơ cấu cảnh báo vận hành" }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: "Biểu đồ khối lượng theo chuyên viên" }),
  ).toBeVisible();

  const refreshed = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/admin/operations/metrics") &&
      response.ok(),
  );
  await page.getByRole("button", { name: "Làm mới dữ liệu" }).click();
  await refreshed;

  await page.getByRole("button", { name: "Giao diện tối" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("body")).not.toHaveCSS("overflow-x", "scroll");
});
