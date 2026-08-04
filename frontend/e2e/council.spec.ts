import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context, request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-council");
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

test("council member attends, declares conflict, votes and sees result", async ({
  page,
}, testInfo) => {
  const consoleIssues: string[] = [];
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleIssues.push(`${message.type()}: ${message.text()}`);
    }
  });

  await page.goto("/hoi-dong");
  await expect(
    page.getByRole("heading", { level: 1, name: "Phiên xét duyệt" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Mở phiên" }).click();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Phiên xét duyệt thương hiệu số",
    }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Xác nhận tham dự" }).click();
  await expect(page.getByText("1/1 tham dự · quorum 1")).toBeVisible();
  await page.getByRole("button", { name: "Mở biểu quyết" }).click();
  await expect(
    page.getByRole("heading", { name: "Xác nhận xung đột lợi ích" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Tôi không có xung đột" }).click();
  await page.getByRole("button", { name: "Biểu quyết hồ sơ" }).click();
  await page.getByRole("button", { name: "Phê duyệt" }).click();
  await page
    .getByLabel("Lý do biểu quyết")
    .fill("Hồ sơ đáp ứng đầy đủ tiêu chí của Hội đồng.");
  await page.getByRole("button", { name: "Kiểm tra phiếu biểu quyết" }).click();
  await expect(
    page.getByRole("heading", { name: "Xác nhận phiếu biểu quyết" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Xác nhận và gửi phiếu" }).click();
  await expect(page.getByText("Phiếu của bạn đã được ghi nhận")).toBeVisible();

  await page.getByRole("button", { name: "Đóng phiên" }).click();
  await expect(
    page.getByRole("heading", { name: "Phê duyệt hồ sơ" }),
  ).toBeVisible();
  await expect(page.getByText("Dấu vân tay biên bản")).toBeVisible();

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
    path: testInfo.outputPath("council-result.png"),
  });
  expect(consoleIssues).toEqual([]);
});
