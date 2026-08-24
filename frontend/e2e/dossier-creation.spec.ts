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

test("an applicant selects a dossier type and creates a draft", async ({
  page,
}) => {
  await page.goto("/dossiers/new");

  const dossierTypes = page.locator(".dossier-type-option");
  await expect(dossierTypes).toHaveCount(12);
  await dossierTypes.filter({ hasText: "Tác phẩm văn hóa" }).click();
  await page
    .getByLabel("Chủ sở hữu hoặc tác giả")
    .fill("Trung tâm an ninh công nghệ số - CNS");
  await page.getByLabel("Loại hình tác phẩm").selectOption("VISUAL_IDENTITY");
  await page
    .getByLabel("Tên tài sản hoặc tác phẩm")
    .fill("Bộ nhận diện thương hiệu TMI");
  await page
    .getByLabel("Mô tả ngắn")
    .fill("Hồ sơ xác lập nguồn gốc và quyền sở hữu.");
  await page.getByRole("button", { name: "Tạo hồ sơ nháp" }).click();

  await expect(page).toHaveURL(
    /\/dossiers\/9155dbf5-bb3e-449d-8bf0-9572cc642cac$/,
  );
});
