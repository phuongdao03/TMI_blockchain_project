import { expect, test } from "@playwright/test";

test("preparation survives reload, another device and a conflicting edit", async ({
  page,
  context,
  browser,
  request,
}, info) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-preparation");
  await context.addCookies(
    ["cns_access", "cns_refresh", "cns_csrf"].map((name) => ({
      name,
      value:
        name === "cns_csrf"
          ? "e2e-csrf"
          : name === "cns_access"
            ? "e2e-access"
            : "e2e-refresh",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax" as const,
    })),
  );
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/dossiers/new");
  await page.locator(".dossier-type-option").first().click();
  await page.getByRole("button", { name: "Tiếp tục nhập thông tin" }).click();
  await page
    .getByLabel("Tên tài sản hoặc tác phẩm")
    .fill("Di sản đang chuẩn bị");
  await page.getByLabel("Mô tả ngắn").fill("Nội dung chưa hoàn tất");
  await expect(
    page.getByRole("status").filter({ hasText: "Đã lưu dữ liệu chuẩn bị" }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Tên tài sản hoặc tác phẩm")).toHaveValue(
    "Di sản đang chuẩn bị",
  );
  await expect(page.getByLabel("Mô tả ngắn")).toHaveValue(
    "Nội dung chưa hoàn tất",
  );
  const other = await browser.newContext({ baseURL: "http://127.0.0.1:3100" });
  try {
    await other.addCookies(await context.cookies());
    const device = await other.newPage();
    await device.goto("/dossiers/new");
    await expect(device.getByLabel("Tên tài sản hoặc tác phẩm")).toHaveValue(
      "Di sản đang chuẩn bị",
    );
    await device
      .getByLabel("Tên tài sản hoặc tác phẩm")
      .fill("Bản từ thiết bị thứ hai");
    await expect(
      device.getByRole("status").filter({ hasText: "Đã lưu dữ liệu chuẩn bị" }),
    ).toBeVisible();
    await page
      .getByLabel("Tên tài sản hoặc tác phẩm")
      .fill("Bản đang nhập trên máy này");
    await expect(
      page.getByRole("heading", {
        name: "Có thay đổi từ thiết bị hoặc tab khác",
      }),
    ).toBeVisible();
    await expect(page.getByLabel("Tên tài sản hoặc tác phẩm")).toHaveValue(
      "Bản đang nhập trên máy này",
    );
    await page.screenshot({
      path: `../docs/ux-evidence-2026-10-27/preparation-conflict-${info.project.name}.png`,
      fullPage: true,
      scale: "css",
    });
    await page.getByRole("button", { name: "Dùng bản trên tài khoản" }).click();
    await expect(page.getByLabel("Tên tài sản hoặc tác phẩm")).toHaveValue(
      "Bản từ thiết bị thứ hai",
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(errors).toEqual([]);
  } finally {
    await other.close();
  }
});
