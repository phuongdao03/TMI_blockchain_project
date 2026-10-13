import { expect, test, type BrowserContext } from "@playwright/test";

import { selectWorkspaceTheme } from "./workspace-theme";

async function authenticate(
  context: BrowserContext,
  persona: "applicant" | "reviewer",
) {
  await context.addCookies([
    {
      name: "cns_access",
      value: "e2e-access",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "cns_refresh",
      value: "e2e-refresh",
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
    {
      name: "cns_e2e_persona",
      value: persona,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
}

test("applicant preparation and submission read as one sequence", async ({
  context,
  page,
}) => {
  await authenticate(context, "applicant");
  await page.goto("/dossiers/new", { waitUntil: "domcontentloaded" });
  await page
    .locator(".dossier-type-option")
    .filter({ hasText: "Tác phẩm văn hóa" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Tài liệu cần chuẩn bị" }),
  ).toBeVisible();
  expect(await page.locator(".dossier-create-form > section").count()).toBe(1);

  await page.getByRole("button", { name: "Tiếp tục nhập thông tin" }).click();
  await page
    .getByLabel("Tên tài sản hoặc tác phẩm")
    .fill("Bộ nhận diện thương hiệu THV");
  await page
    .getByRole("button", { name: "Tiếp tục thông tin theo loại" })
    .click();
  await page
    .getByLabel("Chủ sở hữu hoặc tác giả")
    .fill("Trung tâm an ninh công nghệ số - THV");
  await page.getByLabel("Loại hình tác phẩm").selectOption("VISUAL_IDENTITY");
  await page.getByRole("button", { name: "Kiểm tra thông tin" }).click();
  await page.getByRole("button", { name: "Tạo hồ sơ nháp" }).click();
  await expect(page).toHaveURL(
    /\/dossiers\/9155dbf5-bb3e-449d-8bf0-9572cc642cac/,
  );
  await expect(page.locator(".dossier-state-summary")).toBeVisible();
  await page.getByRole("button", { name: /Kiểm tra & nộp/ }).click();
  await expect(
    page.getByRole("heading", { name: "Kiểm tra & nộp" }),
  ).toBeVisible();
  expect(
    await page.locator('[aria-label="Kiểm tra trước khi nộp"] > div').count(),
  ).toBe(2);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
});

test("reviewer sees evidence and verdict before optional assistance", async ({
  context,
  page,
  request,
}) => {
  await request.post(
    `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}/api/e2e/reset-review`,
  );
  await authenticate(context, "reviewer");
  await page.goto("/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac", {
    waitUntil: "domcontentloaded",
  });
  await expect(
    page.getByRole("heading", { name: "Phiếu thẩm định hồ sơ" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Bằng chứng về quyền sử dụng nhãn hiệu",
    }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Loại tài liệu: Tài liệu về quyền sử dụng hoặc đại diện nhãn hiệu",
    ),
  ).toBeVisible();
  const assistance = page.locator(".review-assistance");
  await expect(assistance).toBeVisible();
  expect(
    await page.evaluate(() => {
      const main = document.querySelector("#review-form");
      const help = document.querySelector("#review-assistance");
      return Boolean(
        main &&
          help &&
          main.compareDocumentPosition(help) & Node.DOCUMENT_POSITION_FOLLOWING,
      );
    }),
  ).toBe(true);
  const disclosure = assistance.locator("details");
  await expect(disclosure).not.toHaveAttribute("open");
  await disclosure.locator("summary").click();
  await expect(disclosure).toHaveAttribute("open");
  await expect(assistance.getByLabel("Lý do cần hỗ trợ")).toBeVisible();
  await selectWorkspaceTheme(page, "Giao diện tối");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const assistanceColors = await assistance
    .locator("form")
    .evaluate((form) => ({
      background: getComputedStyle(form).backgroundColor,
      color: getComputedStyle(form).color,
    }));
  expect(assistanceColors.background).not.toBe("rgba(255, 255, 255, 0.6)");
  expect(assistanceColors.color).not.toBe("rgb(255, 255, 255)");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
});

test("applicant and reviewer flows fit a tablet without page overflow", async ({
  browser,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  for (const [persona, route, locator] of [
    ["applicant", "/dossiers/new", ".dossier-create-form"],
    [
      "reviewer",
      "/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac",
      ".review-workspace",
    ],
  ] as const) {
    const context = await browser.newContext({
      viewport: { width: 768, height: 1024 },
    });
    try {
      await authenticate(context, persona);
      const page = await context.newPage();
      await page.goto(route, { waitUntil: "domcontentloaded" });
      await expect(page.locator(locator)).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
      ).toBe(true);
    } finally {
      await context.close();
    }
  }
});
