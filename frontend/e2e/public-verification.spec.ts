import { expect, test } from "@playwright/test";

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
