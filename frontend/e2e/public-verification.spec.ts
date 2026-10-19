import { expect, test } from "@playwright/test";

test("certificate issuer stays readable without mobile overflow", async ({
  page,
}) => {
  await page.goto("/verify/demo-token");
  const issuer = page
    .locator(".digital-certificate dd")
    .filter({ hasText: /^Đề cử Tinh Hoa Việt$/ });
  for (const width of [320, 390, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(issuer).toBeVisible();
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth + 1,
        ),
      )
      .toBe(true);
  }
});

test("public verification explains provenance without exposing internals", async ({
  page,
}) => {
  await page.goto("/verify/demo-token");

  await expect(
    page.getByText(
      "Đối chiếu tên tác phẩm, chủ thể và thời điểm xác nhận với thông tin bạn được cung cấp.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Lịch sử xác nhận" }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("listitem")
      .filter({ hasText: "Phiên bản 1" })
      .getByText("Phiên bản 1"),
  ).toBeVisible();
  await expect(
    page.getByText(
      /blockchain|Polygon|PayOS|SHA-256|Mạng ghi nhận|Chi tiết nâng cao|Mã toàn vẹn|0x[0-9a-f]{8}/i,
    ),
  ).toHaveCount(0);
  await expect(page.getByText("Đối chiếu tài liệu")).toHaveCount(0);
  await expect(page.getByLabel("Chọn tài liệu để đối chiếu")).toHaveCount(0);
});

test("certificate work action remains readable in light and dark themes", async ({
  page,
}) => {
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await page.goto("/verify/demo-token");
    const action = page
      .locator(".digital-certificate")
      .getByRole("link", { name: "Xem tác phẩm" });
    await expect(action).toBeVisible();
    await expect(action).toHaveAttribute("href", /\/works\//);
    expect(
      await action.evaluate(
        (element) => element.getBoundingClientRect().height,
      ),
    ).toBeGreaterThanOrEqual(44);
  }
});
