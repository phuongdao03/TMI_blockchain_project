import AxeBuilder from "@axe-core/playwright";
import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import { selectWorkspaceTheme } from "./workspace-theme";

const widths = [390, 768, 1440] as const;
const personas = [
  { name: "viewer", cookie: "public", path: "/", workspace: false },
  { name: "user", cookie: "applicant", path: "/dashboard", workspace: true },
  {
    name: "moderator",
    cookie: "reviewer",
    path: "/dashboard",
    workspace: true,
  },
  {
    name: "super admin",
    cookie: "super-admin",
    path: "/admin/dashboard",
    workspace: true,
  },
] as const;

async function authenticate(
  context: BrowserContext,
  persona: (typeof personas)[number],
) {
  await context.addCookies([
    {
      name: "cns_access",
      value:
        persona.cookie === "super-admin"
          ? "e2e-super-admin-access"
          : "e2e-access",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "cns_e2e_persona",
      value: persona.cookie,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
}

async function setTheme(page: Page, workspace: boolean, theme: "sáng" | "tối") {
  const label = `Giao diện ${theme}` as const;
  if (workspace) await selectWorkspaceTheme(page, label);
  else await page.getByRole("button", { name: label }).click();
  await expect(page.locator("html")).toHaveAttribute(
    "data-theme",
    theme === "sáng" ? "light" : "dark",
  );
}

for (const persona of personas) {
  test(`${persona.name} primary shell stays within mobile/tablet/desktop viewports in both themes`, async ({
    context,
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chrome");
    await authenticate(context, persona);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(persona.path);
    await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
    if (persona.cookie === "super-admin") {
      await expect(
        page.locator('section[aria-label="Chỉ số cần theo dõi"]'),
      ).toBeVisible();
      await expect(page.locator("#job-queue-title")).toBeVisible();
    }

    for (const width of widths) {
      await page.setViewportSize({ width, height: 900 });
      for (const theme of ["sáng", "tối"] as const) {
        await setTheme(page, persona.workspace, theme);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= window.innerWidth + 1,
          ),
          `${persona.name} ${width}px ${theme}: horizontal overflow`,
        ).toBe(true);
        await expect(
          page.getByRole("heading", { level: 1 }).first(),
        ).toBeVisible();
        if (width !== 768) {
          const audit = await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
            .analyze();
          expect(
            audit.violations.map((violation) => ({
              id: violation.id,
              elements: violation.nodes.slice(0, 4).map((node) => ({
                target: node.target,
                data: node.any[0]?.data,
              })),
            })),
            `${persona.name} ${width}px ${theme}: WCAG violations`,
          ).toEqual([]);
        }
      }
    }
  });
}
