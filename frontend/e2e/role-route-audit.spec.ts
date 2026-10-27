import AxeBuilder from "@axe-core/playwright";
import { writeFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import { selectWorkspaceTheme } from "./workspace-theme";

const journeys = [
  {
    persona: "applicant",
    routes: [
      "/dashboard",
      "/dossiers",
      "/dossiers/new",
      "/wallet",
      "/membership",
      "/advertising",
      "/notifications",
      "/account",
    ],
  },
  { persona: "reviewer", routes: ["/reviews"] },
  {
    persona: "super-admin",
    routes: [
      "/admin",
      "/admin/reviews",
      "/admin/users",
      "/admin/payments",
      "/admin/content",
      "/admin/memberships",
      "/admin/advertising",
    ],
  },
];

for (const { persona, routes } of journeys) {
  test(`${persona} routes fit supported widths and expose accessible controls`, async ({
    page,
    context,
  }, info) => {
    test.skip(info.project.name !== "desktop-chrome");
    test.setTimeout(300_000);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await context.addCookies(
      (
        [
          ["cns_access", "e2e-access"],
          ["cns_refresh", "e2e-refresh"],
          ["cns_csrf", "e2e-csrf"],
          ["cns_e2e_persona", persona],
        ] as const
      ).map(([name, value]) => ({
        name,
        value,
        domain: "127.0.0.1",
        path: "/",
        sameSite: "Lax" as const,
      })),
    );
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const report: unknown[] = [];
    for (const route of routes.filter(
      (route) =>
        !process.env.E2E_AUDIT_ROUTE || route === process.env.E2E_AUDIT_ROUTE,
    )) {
      await page.setViewportSize({ width: 1440, height: 1000 });
      await page.goto(route);
      await expect(page.locator("main")).toBeVisible();
      await expect(
        page.getByRole("heading", { level: 1 }).first(),
      ).toBeVisible();
      for (const theme of ["Giao diện sáng", "Giao diện tối"] as const) {
        await selectWorkspaceTheme(page, theme);
        for (const width of [360, 375, 390, 430, 768, 1024, 1440]) {
          await page.setViewportSize({ width, height: 900 });
          await page.evaluate(
            () =>
              new Promise<void>((resolve) =>
                requestAnimationFrame(() =>
                  requestAnimationFrame(() => resolve()),
                ),
              ),
          );
          const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth > innerWidth + 1,
          );
          if (overflow) {
            const elements = await page.locator("main").evaluate((main) =>
              Array.from(main.querySelectorAll("*"))
                .filter(
                  (element) =>
                    element.getBoundingClientRect().right > innerWidth + 1,
                )
                .slice(0, 8)
                .map((element) => ({
                  tag: element.tagName,
                  class: element.className,
                  width: element.getBoundingClientRect().width,
                })),
            );
            console.log(JSON.stringify({ route, width, elements }));
          }
          expect
            .soft(overflow, `${persona} ${route} ${theme} ${width}px overflow`)
            .toBe(false);
          if (width === 390 || width === 1440) {
            const result = await new AxeBuilder({ page })
              .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
              .analyze();
            const violations = result.violations.map(
              ({ id, impact, nodes }) => ({
                id,
                impact,
                targets: nodes.map((node) => ({
                  target: node.target,
                  summary: node.failureSummary,
                })),
              }),
            );
            report.push({ route, theme, width, violations });
            expect
              .soft(violations, `${persona} ${route} ${theme} ${width}px`)
              .toEqual([]);
          }
          if (route === "/admin/content" && (width === 390 || width === 1440))
            await page.screenshot({
              path: `../docs/ux-evidence-2026-10-27/content-${theme === "Giao diện sáng" ? "light" : "dark"}-${width}.png`,
              fullPage: true,
              scale: "css",
            });
        }
      }
    }
    await info.attach("role-route-audit", {
      body: JSON.stringify(report, null, 2),
      contentType: "application/json",
    });
    await writeFile(
      `../docs/ux-evidence-2026-10-27/role-audit-${persona}.json`,
      JSON.stringify(
        {
          widths: [360, 375, 390, 430, 768, 1024, 1440],
          checks: report,
          pageErrors: errors,
        },
        null,
        2,
      ),
    );
    expect(errors).toEqual([]);
  });
}
