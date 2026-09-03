import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context, request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-council");
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
    {
      name: "tmi_e2e_persona",
      value: "super-admin",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
});

test("super admin attends, declares conflict, votes and sees result", async ({
  page,
}, testInfo) => {
  const consoleIssues: string[] = [];
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleIssues.push(`${message.type()}: ${message.text()}`);
    }
  });

  await page.goto("/council");
  await expect(
    page.getByRole("heading", { level: 1, name: "Phiên xét duyệt" }),
  ).toBeVisible();
  const openSessionLink = page.getByRole("link", { name: "Mở phiên" });
  await expect(openSessionLink).toHaveAttribute("href", /\/council\//);
  const sessionHref = await openSessionLink.getAttribute("href");
  if (!sessionHref) {
    throw new Error("Council session link is missing its destination.");
  }
  await page.goto(sessionHref);
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Phiên xét duyệt thương hiệu số",
    }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Xác nhận tham dự" }).click();
  await expect(
    page.getByText("1/1 người đã tham gia · cần tối thiểu 1"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Bắt đầu xét duyệt" }).click();
  await expect(
    page.getByRole("heading", { name: "Tiếp nhận hồ sơ trong phiên này" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Tiếp nhận hồ sơ" }).click();
  await page.getByRole("button", { name: "Gửi kết quả xử lý" }).click();
  await page.getByRole("button", { name: "Phê duyệt" }).click();
  await page
    .getByLabel("Lý do lựa chọn")
    .fill("Hồ sơ đáp ứng đầy đủ tiêu chí của Hội đồng.");
  await page.getByRole("button", { name: "Kiểm tra kết quả" }).click();
  await expect(
    page.getByRole("heading", { name: "Xác nhận kết quả xử lý" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Xác nhận và gửi kết quả" }).click();
  await expect(
    page.getByText("Kết quả của bạn đã được ghi nhận"),
  ).toBeVisible();

  await page.getByRole("button", { name: "Kết thúc phiên" }).click();
  await expect(
    page.getByRole("heading", { name: "Phê duyệt hồ sơ" }),
  ).toBeVisible();
  await expect(page.getByText("Mã đối chiếu biên bản")).toBeVisible();

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
