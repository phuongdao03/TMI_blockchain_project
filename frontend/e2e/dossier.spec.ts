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

test("applicant creates, uploads evidence and submits an immutable dossier", async ({
  page,
}, testInfo) => {
  const consoleIssues: string[] = [];
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleIssues.push(`${message.type()}: ${message.text()}`);
    }
  });

  await page.goto("/dossiers");
  await expect(
    page.getByRole("heading", { level: 1, name: "Hồ sơ xác lập" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Tạo hồ sơ mới" }).click();

  await page
    .getByLabel("Tên tài sản hoặc tác phẩm")
    .fill("Bộ nhận diện TMI E2E");
  await page.getByLabel("Mô tả ngắn").fill("Hồ sơ kiểm thử luồng xác lập.");
  await page.getByRole("button", { name: "Tạo hồ sơ nháp" }).click();
  await expect(page).toHaveURL(/\/dossiers\/9155dbf5-/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Bộ nhận diện TMI E2E" }),
  ).toBeVisible();

  await page.getByRole("button", { name: /Bằng chứng/ }).click();
  await page.getByLabel("Tên bằng chứng").fill("Bản gốc nhận diện");
  await page.getByLabel("Chọn bằng chứng hồ sơ").setInputFiles({
    name: "evidence.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nXsAAAAASUVORK5CYII=",
      "base64",
    ),
  });
  await page.getByRole("button", { name: "Tải lên" }).click();
  await expect(page.getByText("Bản gốc nhận diện")).toBeVisible();

  await page.getByRole("button", { name: /Kiểm tra & nộp/ }).click();
  await page.getByRole("button", { name: "Nộp hồ sơ" }).click();
  await expect(
    page.getByText("Hồ sơ đã nộp và đang ở chế độ chỉ đọc."),
  ).toBeVisible();
  const overflow = await page.evaluate(() => {
    const width = document.documentElement.clientWidth;
    return Array.from(document.querySelectorAll<HTMLElement>("body *"))
      .map((element) => ({
        className: element.className,
        right: Math.round(element.getBoundingClientRect().right),
        tag: element.tagName,
        text: element.textContent?.trim().slice(0, 60),
      }))
      .filter(({ right }) => right > width + 1)
      .slice(0, 8);
  });
  expect(overflow).toEqual([]);
  await page.screenshot({
    fullPage: false,
    path: testInfo.outputPath("dossier-submitted.png"),
  });
  expect(consoleIssues).toEqual([]);
});
