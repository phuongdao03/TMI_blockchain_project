import { expect, test } from "@playwright/test";

test("certificate organization stays on one line without overflow", async ({
  page,
}) => {
  await page.goto("/verify/demo-token");
  const organization = page.locator(".digital-certificate__platform");
  for (const width of [320, 390, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(organization).toHaveCSS("white-space", "nowrap");
    await expect
      .poll(() =>
        organization.evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
      )
      .toBe(true);
  }
});

test("public verification explains provenance without document comparison", async ({
  page,
}) => {
  await page.goto("/verify/demo-token");

  await expect(
    page.getByText("Chứng thư hợp lệ và đã được xác nhận trên blockchain."),
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
  const advancedDetails = page.locator("details").filter({
    has: page.getByText("Chi tiết nâng cao", { exact: true }),
  });
  await expect(advancedDetails.getByText("Mạng ghi nhận")).not.toBeVisible();

  await expect(page.getByText("Đối chiếu tài liệu")).toHaveCount(0);
  await expect(page.getByLabel("Chọn tài liệu để đối chiếu")).toHaveCount(0);

  await advancedDetails.getByText("Chi tiết nâng cao", { exact: true }).click();
  await expect(advancedDetails.getByText("Mạng ghi nhận")).toBeVisible();
});

test("certificate work action remains readable in light and dark themes", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/verify/demo-token");
  const action = page.locator(".digital-certificate footer a");
  await expect(action).toBeVisible();
  await expect(action).toContainText("Xem tác phẩm");
  await expect(action).toHaveCSS("color", "rgb(255, 255, 255)");
  await expect(action.locator("svg")).toHaveCSS("color", "rgb(255, 255, 255)");
  await expect(action).toHaveCSS("min-height", "48px");
  await action.hover();
  await expect(action).toHaveCSS("color", "rgb(255, 255, 255)");
  await action.focus();
  await expect(action).toHaveCSS("outline-width", "3px");
  await expect(action).toHaveAttribute("href", /\/works\//);
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(action).toHaveCSS("color", "rgb(255, 255, 255)");
});
