import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context, request }) => {
  const mockPort = process.env.E2E_MOCK_PORT ?? "4010";
  await request.post(`http://127.0.0.1:${mockPort}/api/e2e/reset-cms`);
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
  await page.getByRole("button", { name: /Di sản số CNS/ }).click();
  await expect(page.getByLabel("Tiêu đề công khai")).toHaveValue(
    "Di sản số CNS",
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

test("mobile work preview uses its own width instead of desktop breakpoints", async ({
  page,
  isMobile,
}) => {
  await page.setViewportSize({ width: isMobile ? 390 : 1440, height: 1000 });
  await page.goto("/admin/content");
  await page.getByRole("button", { name: /Di sản số CNS/ }).click();
  await page
    .getByLabel("Tiêu đề công khai")
    .fill("Video chào mừng thương hiệu ĐỀ CỬ TINH HOA VIỆT");
  await page.getByRole("button", { name: "Xem trước", exact: true }).click();
  await page.getByRole("button", { name: "Xem bản mobile" }).click();
  const title = page.getByRole("heading", {
    level: 1,
    name: "Video chào mừng thương hiệu ĐỀ CỬ TINH HOA VIỆT",
    exact: true,
  });
  await expect(title).toBeVisible();
  await expect
    .poll(() =>
      title.evaluate((el) => parseFloat(getComputedStyle(el).fontSize)),
    )
    .toBeLessThanOrEqual(36);
  await expect
    .poll(() => title.evaluate((el) => el.getBoundingClientRect().width))
    .toBeGreaterThan(270);
  await expect
    .poll(() =>
      title.evaluate(
        (el) =>
          getComputedStyle(
            el.parentElement!.parentElement!,
          ).gridTemplateColumns.split(" ").length,
      ),
    )
    .toBe(1);
  for (const width of [320, 390, 768]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth - window.innerWidth,
        ),
      )
      .toBeLessThanOrEqual(1);
    await expect(title).toBeVisible();
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await title.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: test.info().outputPath("mobile-work-preview.png"),
  });
});

test("public work stays readable without horizontal scrolling on phones", async ({
  page,
}) => {
  for (const width of [320, 390, 430, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/works/bo-nhan-dien-cns");
    const title = page.getByRole("heading", {
      level: 1,
      name: "Bộ nhận diện CNS",
      exact: true,
    });
    await expect(title).toBeVisible();
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth - window.innerWidth,
        ),
      )
      .toBeLessThanOrEqual(1);
    if (width < 640) {
      await expect(title).toHaveCSS("font-size", "30px");
      await expect
        .poll(() =>
          title.evaluate(
            (el) =>
              getComputedStyle(
                el.parentElement!.parentElement!,
              ).gridTemplateColumns.split(" ").length,
          ),
        )
        .toBe(1);
    }
  }
});
