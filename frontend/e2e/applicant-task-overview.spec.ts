import { expect, test } from "@playwright/test";

test("applicant sees older actionable dossiers at every viewport in both themes", async ({
  page,
  context,
}, testInfo) => {
  await context.addCookies(
    (
      [
        ["cns_access", "e2e-access"],
        ["cns_refresh", "e2e-refresh"],
        ["cns_csrf", "e2e-csrf"],
        ["cns_e2e_persona", "applicant"],
      ] as const
    ).map(([name, value]) => ({
      name,
      value,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax" as const,
    })),
  );
  await page.route("**/api/v1/dossiers?*", async (route) => {
    const status =
      new URL(route.request().url()).searchParams.get("status") ??
      "UNDER_REVIEW";
    const id = status.toLowerCase();
    const titles: Record<string, string> = {
      NEEDS_SUPPLEMENT: "Di sản làng nghề truyền thống",
      PAYMENT_PENDING: "Sáng kiến gìn giữ văn hóa Việt",
      DRAFT: "Câu chuyện nghề gốm quê hương",
      UNDER_REVIEW: "Giá trị tri thức cộng đồng",
    };
    await route.fulfill({
      json: {
        success: true,
        data: [
          {
            id,
            status,
            code: `THV-${id}`,
            title: titles[status],
            updatedAt: "2026-10-20T00:00:00Z",
          },
        ],
        meta: { page: 1, pageSize: 3, total: 1 },
      },
    });
  });
  const errors: string[] = [];
  await page.route("**/api/v1/wallet", (route) =>
    route.fulfill({
      json: {
        success: true,
        data: {
          balanceMinor: 1250000,
          currency: "VND",
          provider: "mock",
          transactions: [],
          topups: [],
        },
      },
    }),
  );
  await page.route("**/api/v1/notifications/unread-count", (route) =>
    route.fulfill({ json: { success: true, data: { unreadCount: 3 } } }),
  );
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/dashboard");
  const account = page.getByRole("region", { name: "Ví và thông báo" });
  await expect(account.getByText(/1\.250\.000\s*₫/)).toBeVisible();
  await expect(account.getByText("3 thông báo chưa đọc")).toBeVisible();
  const tasks = page.getByRole("region", { name: "Cần bạn xử lý" });
  await expect(tasks.getByRole("link")).toHaveCount(3);
  await expect(tasks.getByRole("link").first()).toHaveAttribute(
    "href",
    "/dossiers/needs_supplement",
  );
  await expect(page.getByRole("link", { name: "Tạo hồ sơ mới" })).toBeVisible();
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await expect(page.locator("html")).toHaveAttribute(
      "data-theme",
      colorScheme,
    );
    for (const width of [360, 375, 390, 430, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await expect(tasks).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      if ([390, 1440].includes(width)) {
        await page.screenshot({
          path: testInfo.outputPath(`tasks-${colorScheme}-${width}.png`),
          fullPage: true,
          scale: "css",
        });
        await page.screenshot({
          path: `../docs/ux-evidence-2026-10-27/account-summary-${colorScheme}-${width}.png`,
          fullPage: true,
          scale: "css",
        });
      }
    }
  }
  await tasks.getByRole("link").first().focus();
  await expect(tasks.getByRole("link").first()).toBeFocused();
  expect(errors).toEqual([]);
});

test("public hero exposes nomination and discovery on mobile and desktop", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  const hero = page.locator(".registry-hero");
  for (const width of [360, 375, 390, 430, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(
      hero.getByRole("link", { name: "Gửi hồ sơ đề cử" }),
    ).toBeVisible();
    if (width <= 430) {
      const action = await hero
        .getByRole("link", { name: "Gửi hồ sơ đề cử" })
        .boundingBox();
      expect(action).not.toBeNull();
      expect(action!.y + action!.height).toBeLessThan(800);
    }
    await expect(
      hero.getByRole("link", { name: "Khám phá đề cử" }),
    ).toBeVisible();
    await expect(
      hero.getByRole("link", { name: "Xem quy trình" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    if ([390, 1440].includes(width))
      await page.screenshot({
        path: testInfo.outputPath(`home-${width}.png`),
        scale: "css",
      });
  }
  await hero.getByRole("link", { name: "Gửi hồ sơ đề cử" }).click();
  await expect(page).toHaveURL(/\/login\?next=%2Fdossiers%2Fnew/);
});
