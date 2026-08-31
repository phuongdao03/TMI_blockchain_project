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

test("critical MVP journey reaches a publicly verifiable certificate", async ({
  context,
  page,
  request,
}) => {
  test.setTimeout(90_000);
  const consoleIssues: string[] = [];
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleIssues.push(`${message.type()}: ${message.text()}`);
    }
  });

  await test.step("applicant creates, uploads and submits dossier", async () => {
    await page.goto("/dossiers");
    await page.getByRole("link", { name: "Tạo hồ sơ mới" }).click();
    await page
      .locator(".dossier-type-option")
      .filter({ hasText: "Tác phẩm văn hóa" })
      .click();
    await page
      .getByLabel("Chủ sở hữu hoặc tác giả")
      .fill("Trung tâm an ninh công nghệ số - CNS");
    await page.getByLabel("Loại hình tác phẩm").selectOption("VISUAL_IDENTITY");
    await page
      .getByLabel("Tên tài sản hoặc tác phẩm")
      .fill("Bộ nhận diện TMI Critical Journey");
    await page.getByLabel("Mô tả ngắn").fill("Hồ sơ E2E toàn luồng MVP.");
    await page.getByRole("button", { name: "Tạo hồ sơ nháp" }).click();
    await expect(page).toHaveURL(/\/dossiers\/9155dbf5-/);
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
    await page.getByRole("button", { name: "Tải lên", exact: true }).click();
    await page.getByRole("button", { name: /Kiểm tra & nộp/ }).click();
    await page.getByRole("button", { name: "Nộp hồ sơ" }).click();
    await expect(page.getByText(/chế độ chỉ đọc/)).toBeVisible();
  });

  await test.step("reviewer completes conflict gate and 5T review", async () => {
    await request.post("http://127.0.0.1:4010/api/e2e/reset-review");
    await context.addCookies([
      {
        name: "tmi_e2e_persona",
        value: "reviewer",
        domain: "127.0.0.1",
        path: "/",
        httpOnly: false,
        sameSite: "Lax",
      },
    ]);
    await page.goto("/reviews");
    await page.getByRole("link", { name: "Mở hồ sơ thẩm định" }).click();
    await page.getByRole("button", { name: "Tôi không có xung đột" }).click();
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
        .fill(`Đánh giá đầy đủ cho ${criterion}.`);
    }
    const checklist = page.getByRole("checkbox");
    await expect(checklist).toHaveCount(10);
    for (let index = 0; index < 10; index += 1) {
      await checklist.nth(index).check();
    }
    const autosave = page.waitForResponse(
      (response) =>
        response.url().endsWith("/draft") &&
        response.request().method() === "PUT" &&
        response.ok(),
    );
    await page.getByLabel("Kiến nghị").selectOption("APPROVE");
    await autosave;
    await page.getByRole("button", { name: "Gửi kết quả thẩm định" }).click();
    await page.getByRole("button", { name: "Xác nhận gửi" }).click();
    await expect(page.getByText(/không thể chỉnh sửa/)).toBeVisible();
  });

  await test.step("council attends, votes and approves", async () => {
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
        name: "tmi_e2e_persona",
        value: "super-admin",
        domain: "127.0.0.1",
        path: "/",
        httpOnly: false,
        sameSite: "Lax",
      },
    ]);
    await page.goto("/council");
    await page.getByRole("link", { name: "Mở phiên" }).click();
    await page.getByRole("button", { name: "Xác nhận tham dự" }).click();
    await page.getByRole("button", { name: "Mở biểu quyết" }).click();
    await page.getByRole("button", { name: "Tôi không có xung đột" }).click();
    await page.getByRole("button", { name: "Biểu quyết hồ sơ" }).click();
    await page.getByRole("button", { name: "Phê duyệt" }).click();
    await page
      .getByLabel("Lý do biểu quyết")
      .fill("Hồ sơ đáp ứng đầy đủ tiêu chí Hội đồng.");
    await page
      .getByRole("button", { name: "Kiểm tra phiếu biểu quyết" })
      .click();
    await page.getByRole("button", { name: "Xác nhận và gửi phiếu" }).click();
    await page.getByRole("button", { name: "Đóng phiên" }).click();
    await expect(
      page.getByRole("heading", { name: "Phê duyệt hồ sơ" }),
    ).toBeVisible();
  });

  await test.step("payment is confirmed by trusted status", async () => {
    await request.post("http://127.0.0.1:4010/api/e2e/reset-payment-pending");
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
        name: "tmi_e2e_persona",
        value: "applicant",
        domain: "127.0.0.1",
        path: "/",
        httpOnly: false,
        sameSite: "Lax",
      },
    ]);
    await page.goto("/payments/a255dbf5-bb3e-449d-8bf0-9572cc642cac");
    await expect(
      page.getByRole("heading", { name: "Thanh toán thành công" }),
    ).toBeVisible({ timeout: 10_000 });
  });

  await test.step("anchored certificate is visible and verifiable", async () => {
    await page.goto("/certificates");
    await expect(page.getByText("TMI-2026-7EAEC2D2C99A")).toBeVisible();
    await page.goto("/verify");
    await page
      .getByLabel("Thông tin cần tra cứu")
      .fill("TMI-2026-7EAEC2D2C99A");
    await page.getByRole("button", { name: "Kiểm tra" }).click();
    await expect(
      page.getByText("Dữ liệu đã được ghi nhận và không thay đổi"),
    ).toBeVisible();
  });

  expect(consoleIssues).toEqual([]);
});
