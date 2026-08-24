import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { BrowserContext } from "@playwright/test";

const viewports = [
  { width: 320, height: 844 },
  { width: 768, height: 1024 },
  { width: 1024, height: 900 },
  { width: 1440, height: 1000 },
] as const;

const forbiddenPublicTerms =
  /\b(?:ADMIN|REVIEWER|COUNCIL_MEMBER|SUPER_ADMIN|database|schema|backend|API|endpoint|CSRF|audit trail|workspace)\b/i;
const forbiddenApplicantTerms =
  /\b(?:ADMIN|REVIEWER|COUNCIL_MEMBER|SUPER_ADMIN|database|schema|backend|API|endpoint|CSRF|audit trail|workspace|blockchain)\b/i;

async function authenticateApplicant(context: BrowserContext) {
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
      name: "tmi_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
    {
      name: "tmi_e2e_persona",
      value: "applicant",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
}

test("public experience passes visual and accessibility gates at all supported widths", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);

    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toMatch(forbiddenPublicTerms);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);

    const accessibility = await new AxeBuilder({ page }).analyze();
    expect(accessibility.violations).toEqual([]);
    await expect.soft(page).toHaveScreenshot(`public-${viewport.width}.png`, {
      animations: "disabled",
      fullPage: true,
    });
  }
});

test("applicant dossier journey stays readable at all supported widths", async ({
  context,
  page,
  request,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await request.post("http://127.0.0.1:4010/api/e2e/reset-needs-supplement");
  await authenticateApplicant(context);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/dossiers/9155dbf5-bb3e-449d-8bf0-9572cc642cac");
  await expect(
    page.getByRole("heading", { level: 1, name: "Hồ sơ cần bổ sung" }),
  ).toBeVisible();

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toMatch(forbiddenApplicantTerms);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);
    await expect
      .soft(page)
      .toHaveScreenshot(`applicant-${viewport.width}.png`, {
        animations: "disabled",
        fullPage: true,
      });
  }
});

test("public navigation and primary actions remain keyboard accessible", async ({
  page,
}) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect
    .poll(() =>
      page.evaluate(() => {
        const active = document.activeElement;
        return (
          active instanceof HTMLElement &&
          active.matches("a, button, input, select, textarea") &&
          active.getBoundingClientRect().width > 0
        );
      }),
    )
    .toBe(true);

  const primaryAction = page.locator('a[href="/register"]:visible').first();
  await primaryAction.focus();
  await expect(primaryAction).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/(?:login|register)/);
});

test("verification remains readable in explicit light and dark themes", async ({
  page,
}) => {
  await page.goto("/verify");

  for (const theme of [
    { label: "Giao diện sáng", value: "light" },
    { label: "Giao diện tối", value: "dark" },
  ]) {
    await page.getByRole("button", { name: theme.label }).click();
    await expect(page.locator("html")).toHaveAttribute(
      "data-theme",
      theme.value,
    );
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const accessibility = await new AxeBuilder({ page }).analyze();
    expect(accessibility.violations).toEqual([]);
  }
});
