import { expect, test, type BrowserContext } from "@playwright/test";

async function signInAs(
  context: BrowserContext,
  persona: "applicant" | "reviewer" | "super-admin",
) {
  await context.addCookies([
    {
      name: "cns_access",
      value:
        persona === "super-admin" ? "e2e-super-admin-access" : "e2e-access",
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

test("document preparation precedes the dossier type list", async ({
  context,
  page,
}) => {
  await signInAs(context, "applicant");
  await page.goto("/dossiers/new", { waitUntil: "domcontentloaded" });

  const firstType = page.locator(".dossier-type-option").first();
  await expect(firstType).toBeVisible();
  await firstType.click();

  const preparation = page.locator(".dossier-preflight");
  await expect(preparation).toBeVisible();
  await expect
    .poll(async () => {
      const preparationBox = await preparation.boundingBox();
      const firstTypeBox = await firstType.boundingBox();
      return Boolean(
        preparationBox &&
          firstTypeBox &&
          preparationBox.y + preparationBox.height <= firstTypeBox.y,
      );
    })
    .toBe(true);

  if (page.viewportSize()!.width < 640) {
    await page.locator(".dossier-type-option").last().click();
    await expect(preparation).toBeInViewport();
  }
});

test("Admin module icons stay compact within a rounded section", async ({
  context,
  page,
}) => {
  await signInAs(context, "super-admin");
  await page.goto("/admin", { waitUntil: "domcontentloaded" });

  const moduleList = page.locator(".admin-module-list");
  await expect(moduleList.locator("a").first()).toBeVisible();
  const layout = await moduleList.evaluate((list) => {
    const firstRow = list.querySelector("a");
    const icon = firstRow?.firstElementChild;
    return {
      sectionRadius: parseFloat(getComputedStyle(list).borderTopLeftRadius),
      iconHeight: icon?.getBoundingClientRect().height ?? 0,
      rowHeight: firstRow?.getBoundingClientRect().height ?? 0,
      overflow: document.documentElement.scrollWidth > innerWidth + 1,
    };
  });
  expect(layout.sectionRadius).toBeGreaterThanOrEqual(16);
  expect(layout.iconHeight).toBeLessThan(60);
  expect(layout.rowHeight).toBeGreaterThan(layout.iconHeight);
  expect(layout.overflow).toBe(false);
  await moduleList.locator("a").first().hover();
  expect(
    await moduleList
      .locator("a")
      .first()
      .evaluate((row) => getComputedStyle(row).backgroundColor),
  ).not.toBe("rgba(0, 0, 0, 0)");
});

test("leave workspace keeps its surfaces restrained", async ({
  context,
  page,
}) => {
  await signInAs(context, "reviewer");
  await page.goto("/leave", { waitUntil: "domcontentloaded" });

  const workspace = page.locator('section[aria-labelledby="leave-title"]');
  await expect(workspace.locator("form")).toBeVisible();
  const radii = await workspace.evaluate((section) => ({
    hero: parseFloat(
      getComputedStyle(section.querySelector("header")!).borderTopLeftRadius,
    ),
    form: parseFloat(
      getComputedStyle(section.querySelector("form")!).borderTopLeftRadius,
    ),
    overflow: document.documentElement.scrollWidth > innerWidth + 1,
  }));
  expect(radii.hero).toBeLessThanOrEqual(12);
  expect(radii.form).toBeLessThanOrEqual(12);
  expect(radii.overflow).toBe(false);
});

test("reported pages fit the tablet viewport", async ({
  browser,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");

  for (const [persona, route, selector] of [
    ["applicant", "/dossiers/new", ".dossier-type-option"],
    ["super-admin", "/admin", ".admin-module-list a"],
    ["reviewer", "/leave", 'section[aria-labelledby="leave-title"] form'],
  ] as const) {
    const context = await browser.newContext({
      viewport: { width: 768, height: 1024 },
    });
    try {
      await signInAs(context, persona);
      const page = await context.newPage();
      await page.goto(route, { waitUntil: "domcontentloaded" });
      await expect(page.locator(selector).first()).toBeVisible();
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
