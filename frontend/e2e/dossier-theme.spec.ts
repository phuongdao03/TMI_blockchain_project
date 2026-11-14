import { expect, test } from "@playwright/test";

import { selectWorkspaceTheme } from "./workspace-theme";

test("dark mode keeps submitted dossier notices and workflow readable", async ({
  page,
  request,
}) => {
  await request.post(
    `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}/api/e2e/reset-payment`,
  );
  await page.goto("/dossiers/9155dbf5-bb3e-449d-8bf0-9572cc642cac");
  await selectWorkspaceTheme(page, "Giao diện tối");

  const summary = page.locator(".dossier-workspace > header");
  const workflow = page.getByRole("region", {
    name: "Tiến độ hồ sơ",
    exact: true,
  });
  await expect(summary).toBeVisible();
  await expect(workflow).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Các bước hoàn thiện hồ sơ" }),
  ).toHaveCount(0);
  await expect(summary).toHaveCSS("color", "rgb(255, 249, 243)");
  await expect(workflow).toHaveCSS("color", "rgb(255, 249, 243)");
  await workflow.getByText("Xem toàn bộ tiến độ", { exact: true }).click();
  await expect(workflow.getByText("Từ chuẩn bị đến công bố")).toBeVisible();
});

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
    {
      name: "cns_e2e_persona",
      value: "applicant",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
});

test("dark mode keeps the selected dossier visibility card readable", async ({
  page,
}) => {
  await page.goto("/dossiers/new");
  await selectWorkspaceTheme(page, "Giao diện tối");
  await page
    .locator(".dossier-type-option")
    .filter({ hasText: "Tác phẩm văn hóa" })
    .click();
  await page.getByRole("button", { name: "Tiếp tục nhập thông tin" }).click();

  const privateOption = page
    .locator(".dossier-visibility-option")
    .filter({ hasText: "Riêng tư" });
  await expect(privateOption).not.toHaveCSS(
    "background-color",
    "rgb(243, 246, 240)",
  );
  await expect(
    privateOption.getByText("Riêng tư", { exact: true }),
  ).toBeVisible();
});
