import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context, request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-review");
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

test("reviewer acknowledges conflict gate, reviews evidence and submits 5T", async ({
  page,
}, testInfo) => {
  const consoleIssues: string[] = [];
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleIssues.push(`${message.type()}: ${message.text()}`);
    }
  });

  await page.goto("/reviews");
  await expect(
    page.getByRole("heading", { level: 1, name: "Hàng đợi thẩm định" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Mở hồ sơ thẩm định" }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: "Hồ sơ thương hiệu TMI" }),
  ).toBeVisible();
  await expect(page.getByText("Bằng chứng phiên bản đã khóa")).toHaveCount(0);

  await page.getByRole("button", { name: "Tôi không có xung đột" }).click();
  await expect(page.getByText("Bằng chứng phiên bản đã khóa")).toBeVisible();
  await expect(page.getByText("Giấy xác nhận quyền sở hữu")).toBeVisible();

  const popupPromise = page.waitForEvent("popup");
  await page.getByRole("button", { name: "Xem bằng chứng" }).click();
  const popup = await popupPromise;
  await popup.waitForLoadState();
  await popup.close();

  const criteria = [
    "Tính đúng đắn",
    "Tính minh bạch",
    "Tinh thần trách nhiệm",
    "Tính chuyên nghiệp",
    "Sự tôn trọng",
  ];
  for (const criterion of criteria) {
    await page.getByLabel(`Điểm ${criterion}`).fill("16");
    await page
      .getByLabel(`Nhận xét ${criterion}`)
      .fill(`Đánh giá E2E đầy đủ cho ${criterion}.`);
  }
  const autosave = page.waitForResponse(
    (response) =>
      response.url().endsWith("/draft") &&
      response.request().method() === "PUT" &&
      response.status() === 200,
  );
  await page.getByLabel("Kiến nghị").selectOption("APPROVE");
  await autosave;

  await page.getByRole("button", { name: "Gửi kết quả thẩm định" }).click();
  await expect(
    page.getByRole("heading", { name: "Xác nhận gửi kết quả" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Xác nhận gửi" }).click();
  await expect(
    page.getByText("Kết quả đã gửi và không thể chỉnh sửa."),
  ).toBeVisible();

  const overflow = await page.evaluate(() => {
    const width = document.documentElement.clientWidth;
    return Array.from(document.querySelectorAll<HTMLElement>("body *"))
      .map((element) => ({
        right: Math.round(element.getBoundingClientRect().right),
        tag: element.tagName,
      }))
      .filter(({ right }) => right > width + 1)
      .slice(0, 8);
  });
  expect(overflow).toEqual([]);
  await page.screenshot({
    fullPage: false,
    path: testInfo.outputPath("review-submitted.png"),
  });
  expect(consoleIssues).toEqual([]);
});

test("reviewer resolves a similarity case with a reasoned decision", async ({
  page,
}) => {
  await page.goto("/reviews/similarity");
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Đối chiếu nội dung tương đồng",
    }),
  ).toBeVisible();
  await expect(page.getByText("Bình minh trên sông")).toBeVisible();
  await expect(page.getByText("near-duplicate-v1")).toHaveCount(0);

  const popupPromise = page.waitForEvent("popup");
  await page.getByRole("button", { name: "Xem tài liệu 1" }).first().click();
  const popup = await popupPromise;
  await popup.close();

  await page.getByLabel("Kết luận đối chiếu").selectOption("RELATED");
  await page
    .getByLabel("Căn cứ cho kết luận")
    .fill("Hai tác phẩm thuộc cùng một bộ sưu tập nhưng là hai bản độc lập.");
  await page.getByRole("button", { name: "Hoàn tất đối chiếu" }).click();

  await expect(page.getByText("Đã hoàn tất đối chiếu")).toBeVisible();
});
