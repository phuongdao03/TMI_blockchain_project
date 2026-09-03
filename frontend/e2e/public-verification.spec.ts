import { expect, test } from "@playwright/test";

test("public verification explains provenance and compares a file locally", async ({
  page,
}) => {
  await page.goto("/verify/demo-token");

  await expect(
    page.getByText("Tài liệu đã được ghi nhận và chưa bị thay đổi."),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Lịch sử xác nhận" }),
  ).toBeVisible();
  await expect(page.getByText("Phiên bản 1")).toBeVisible();
  await expect(page.getByText("Mạng ghi nhận")).not.toBeVisible();

  await page.getByLabel("Chọn tài liệu để đối chiếu").setInputFiles({
    name: "proof.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("hello"),
  });
  await expect(page.getByText("Tài liệu trùng khớp")).toBeVisible();

  await page.getByText("Chi tiết nâng cao", { exact: true }).click();
  await expect(page.getByText("Mạng ghi nhận")).toBeVisible();
});
