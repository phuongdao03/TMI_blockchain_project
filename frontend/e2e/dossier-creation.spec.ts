import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { expectDocumentToFit } from "./responsive-layout";
import { selectWorkspaceTheme } from "./workspace-theme";

test.beforeEach(async ({ context, request }) => {
  await request.post(
    `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}/api/e2e/reset-preparation`,
  );
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
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
});

test("organization entry explains optional registration and fits phone-first controls", async ({
  page,
}, testInfo) => {
  await page.goto("/dossiers/new");
  await page
    .locator(".dossier-type-option")
    .filter({ hasText: "Tổ chức, doanh nghiệp" })
    .click();
  await page.getByRole("button", { name: "Tiếp tục nhập thông tin" }).click();
  await page
    .getByLabel("Tên tài sản hoặc tác phẩm")
    .fill("Tổ chức Văn hóa Việt");
  await page
    .getByRole("button", { name: "Tiếp tục thông tin theo loại" })
    .click();
  const registration = page.getByLabel(
    "Số đăng ký của tổ chức/doanh nghiệp (không bắt buộc)",
  );
  await expect(registration).not.toHaveAttribute("required");
  await expect(page.getByText(/Không phải mã hồ sơ/)).toBeVisible();
  await page
    .getByLabel("Người đại diện *", { exact: true })
    .fill("Nguyễn Văn An");
  for (const theme of ["Giao diện sáng", "Giao diện tối"] as const) {
    await selectWorkspaceTheme(page, theme);
    for (const width of [320, 360, 390, 428, 768, 1024, 1280, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await expectDocumentToFit(page, `Organization ${theme} ${width}px`);
      const collapse = page.getByRole("button", {
        name: "Thu gọn thanh điều hướng",
      });
      if (width <= 1024) await expect(collapse).not.toBeVisible();
      else {
        await expect(collapse).toBeVisible();
        const box = await collapse.boundingBox();
        expect(box?.width).toBe(44);
        expect(box?.height).toBe(44);
      }
      if (width <= 428) {
        await expect(registration).toHaveCSS("font-size", "16px");
        const actions = page.locator(".dossier-create-actions");
        await actions.scrollIntoViewIfNeeded();
        const primary = await actions
          .getByRole("button", { name: "Xem lại bản nháp" })
          .boundingBox();
        const area = await actions.boundingBox();
        expect(primary?.width).toBe(area?.width);
        expect(primary?.height).toBeGreaterThanOrEqual(48);
        await page.screenshot({
          path: testInfo.outputPath(`organization-${theme}-${width}.png`),
          fullPage: true,
        });
      }
      if (width === 390 || width === 1440) {
        const accessibility = await new AxeBuilder({ page })
          .include(".dossier-create-form")
          .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
          .analyze();
        expect(accessibility.violations).toEqual([]);
      }
    }
  }
  await page.setViewportSize({ width: 390, height: 900 });
  await page.getByRole("button", { name: "Mở điều hướng workspace" }).click();
  await expect(
    page.getByRole("dialog", { name: "Điều hướng workspace" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Mở điều hướng workspace" }),
  ).toBeFocused();
  await page.getByRole("button", { name: "Xem lại bản nháp" }).click();
  await expect(
    page.getByRole("button", { name: "Tạo hồ sơ nháp" }),
  ).toBeVisible();
});

test("an applicant selects a dossier type and creates a draft", async ({
  page,
}) => {
  await page.goto("/dossiers/new");

  const dossierTypes = page.locator(".dossier-type-option");
  await expect(dossierTypes).toHaveCount(12);
  await dossierTypes.filter({ hasText: "Tác phẩm văn hóa" }).click();
  await page.getByRole("button", { name: "Tiếp tục nhập thông tin" }).click();
  await page
    .getByLabel("Tên tài sản hoặc tác phẩm")
    .fill("Bộ nhận diện thương hiệu THV");
  await page
    .getByLabel("Mô tả ngắn")
    .fill("Hồ sơ xác lập nguồn gốc và quyền sở hữu.");
  await page
    .getByRole("button", { name: "Tiếp tục thông tin theo loại" })
    .click();
  await page
    .getByLabel("Chủ sở hữu hoặc tác giả")
    .fill("Trung tâm an ninh công nghệ số - THV");
  await page.getByLabel("Loại hình tác phẩm").selectOption("VISUAL_IDENTITY");
  await page.getByRole("button", { name: "Xem lại bản nháp" }).click();
  await page.getByRole("button", { name: "Tạo hồ sơ nháp" }).click();

  await expect(page).toHaveURL(
    /\/dossiers\/9155dbf5-bb3e-449d-8bf0-9572cc642cac\?created=1$/,
  );
});
