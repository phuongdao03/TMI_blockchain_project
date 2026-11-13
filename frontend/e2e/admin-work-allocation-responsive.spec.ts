import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { selectWorkspaceTheme } from "./workspace-theme";

const response = (data: unknown) => ({
  success: true,
  data,
  meta: {
    request_id: "admin-work-responsive",
    page: 1,
    pageSize: 50,
    total: 1,
  },
});

test("admin work allocation fits target viewports with readable contrast", async ({
  context,
  page,
}) => {
  await context.addCookies(
    (
      [
        ["cns_access", "e2e-super-admin-access"],
        ["cns_refresh", "e2e-refresh"],
        ["cns_csrf", "e2e-csrf"],
        ["cns_e2e_persona", "super-admin"],
      ] as const
    ).map(([name, value]) => ({
      name,
      value,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax" as const,
    })),
  );

  await page.route("**/api/v1/admin/work-allocations**", (route) =>
    route.fulfill({
      json: response([
        {
          id: "allocation-responsive",
          kind: "GENERIC",
          objective: "Rà soát hồ sơ và đối chiếu minh chứng",
          description: "Kiểm tra tài liệu nguồn gốc.",
          dossierId: null,
          dossierVersionId: null,
          dueAt: null,
          priority: "HIGH",
          status: "ACTIVE",
          createdByUserId: "super-admin",
          createdAt: "2026-11-13T08:00:00Z",
          updatedAt: "2026-11-13T08:00:00Z",
        },
      ]),
    }),
  );
  await page.route("**/api/v1/admin/review-dossiers**", (route) =>
    route.fulfill({ json: response([]) }),
  );
  await page.route("**/api/v1/admin/staff-accounts**", (route) =>
    route.fulfill({ json: response([]) }),
  );

  await page.goto("/admin/work-allocations");
  await expect(page.locator("#work-allocations-title")).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Rà soát hồ sơ và đối chiếu minh chứng",
    }),
  ).toBeVisible();
  const hero = page.locator("header").filter({
    has: page.locator("#work-allocations-title"),
  });
  await expect(hero).toHaveCSS("background-color", "rgb(36, 21, 21)");

  for (const width of [320, 375, 390, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 960 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
      `Admin work allocation should fit at ${width}px`,
    ).toBe(true);
    await page.screenshot({
      path: test.info().outputPath(`admin-work-allocation-${width}.png`),
      fullPage: true,
    });
  }

  for (const [width, theme] of [
    [390, "Giao diện tối"],
    [1440, "Giao diện sáng"],
  ] as const) {
    await page.setViewportSize({ width, height: 960 });
    await selectWorkspaceTheme(page, theme);
    const accessibility = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(accessibility.violations).toEqual([]);
  }
});
