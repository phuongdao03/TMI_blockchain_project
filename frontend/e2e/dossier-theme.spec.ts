import { expect, test } from "@playwright/test";

test("dark mode keeps submitted dossier notices and workflow readable", async ({
  page,
  request,
}) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-payment");
  await page.goto("/dossiers/9155dbf5-bb3e-449d-8bf0-9572cc642cac");
  await page.getByRole("button", { name: "Giao diện tối" }).click();

  const summary = page.locator(".dossier-state-card");
  const readonlyNotice = page.locator(".dossier-readonly-notice");
  const workflow = page.locator(".dossier-workflow");

  await expect(summary).toBeVisible();
  await expect(readonlyNotice).toBeVisible();
  await expect(workflow).toBeVisible();
  await expect(summary).not.toHaveCSS("background-color", "rgb(243, 246, 240)");
  await expect(readonlyNotice).not.toHaveCSS(
    "background-color",
    "rgb(239, 246, 255)",
  );
  await expect(workflow).not.toHaveCSS(
    "background-color",
    "rgb(255, 255, 255)",
  );

  const noticeColors = await readonlyNotice.evaluate((element) => ({
    background: getComputedStyle(element).backgroundColor,
    text: getComputedStyle(element).color,
  }));
  expect(noticeColors.background).not.toBe("rgb(239, 246, 255)");
  expect(noticeColors.text).not.toBe("rgb(30, 58, 138)");
});

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
    {
      name: "tmi_e2e_persona",
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
  await page.getByRole("button", { name: "Giao diện tối" }).click();

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
