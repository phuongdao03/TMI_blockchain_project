import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context }) => {
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

test("account page presents profile and permission-aware organization UI", async ({
  page,
}) => {
  await page.goto("/account");

  await expect(
    page.getByRole("heading", { level: 1, name: "Tài khoản & tổ chức" }),
  ).toBeVisible();
  await expect(page.getByLabel("Họ và tên")).toHaveValue("Nguyễn Minh Anh");
  await page.getByLabel("Chọn ảnh đại diện").setInputFiles({
    name: "avatar.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nXsAAAAASUVORK5CYII=",
      "base64",
    ),
  });
  await page.getByRole("button", { name: "Tải lên" }).click();
  await expect(page.getByText("Ảnh đại diện đã được liên kết")).toBeVisible();
  await expect(
    page.getByText("Tệp đã được tải lên và xác minh."),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Tổ chức" }).click();
  await expect(page.getByLabel("Tên hiển thị")).toHaveValue("TMI Lab");
  await expect(
    page.getByRole("button", { name: "Mời thành viên" }),
  ).toBeVisible();
  await expect(page.getByText("member@tmigroup.vn")).toBeVisible();
});
