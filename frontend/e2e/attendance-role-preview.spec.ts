import { expect, test, type BrowserContext, type Page } from "@playwright/test";

async function setRolePreviewCookie(
  context: BrowserContext,
  role: "reviewer" | "super-admin",
) {
  const superAdmin = role === "super-admin";
  await context.addCookies([
    {
      name: "cns_access",
      value: superAdmin ? "e2e-super-admin-access" : "e2e-access",
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
      value: role,
      domain: "127.0.0.1",
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
}

async function expectNoHorizontalOverflow(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          document.documentElement.scrollWidth <=
          document.documentElement.clientWidth + 1,
      ),
    )
    .toBe(true);
}

test("moderator attendance preview shows a populated current workday", async ({
  context,
  page,
}) => {
  await setRolePreviewCookie(context, "reviewer");

  await page.goto("/attendance");

  await expect(
    page.getByRole("heading", { level: 1, name: "Chấm công cá nhân" }),
  ).toBeVisible();
  await expect(page.getByText("Bạn đang trong ca")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Chấm công ra" }),
  ).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("moderator dashboard shows personal HR summary and self-service links", async ({
  context,
  page,
}) => {
  await setRolePreviewCookie(context, "reviewer");

  await page.goto("/dashboard");

  const personalSummary = page.locator(
    'section[aria-labelledby="moderator-hr-dashboard-title"]',
  );
  await expect(personalSummary).toBeVisible();
  await expect(personalSummary.locator('a[href="/leave"]')).toContainText("1");
  await expect(personalSummary.locator('a[href="/overtime"]')).toContainText(
    "2",
  );
  await expectNoHorizontalOverflow(page);
});

test("moderator assignment notice routes to the work allocation safely", async ({
  context,
  page,
}) => {
  await setRolePreviewCookie(context, "reviewer");
  await page.goto("/notifications");

  const notice = page.locator(
    '.notification-center__list a[href="/work-allocations"]',
  );
  await expect(notice).toBeVisible();
  await expect(notice).not.toContainText("PRIVATE_DOSSIER_SENTINEL");
});

test("super admin previews the populated attendance feed and circle worksite map", async ({
  context,
  page,
}) => {
  await setRolePreviewCookie(context, "super-admin");

  await page.goto("/admin/attendance");

  await expect(
    page.getByRole("heading", { level: 1, name: "Chấm công toàn đội" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Vị trí cần xét duyệt" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Jordan Lee.*DEMO-002/ }),
  ).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.goto("/admin/attendance/worksites");

  await expect(
    page.getByRole("heading", { level: 1, name: "Địa điểm làm việc toàn cầu" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /DEMO-SG.*Singapore/ }),
  ).toBeVisible();
  await expect(
    page.locator('[aria-label="Bản đồ cấu hình vùng chấm công"]'),
  ).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.goto("/admin/attendance");
  await page.locator(".notification-bell__trigger").click();
  const notificationDialog = page.getByRole("dialog", {
    name: "Thông báo gần đây",
  });
  await expect(
    notificationDialog.getByRole("link", { name: /Cần xác minh chấm công/ }),
  ).toBeVisible();
  await expect(notificationDialog).not.toContainText("1.356500");
});

test("admin notification center routes leave requests without sensitive details", async ({
  context,
  page,
}) => {
  await setRolePreviewCookie(context, "super-admin");
  await page.goto("/notifications");

  const notificationList = page.locator(".notification-center__list");
  const leaveNotice = notificationList.locator('a[href="/admin/leave"]');
  const overtimeNotice = notificationList.locator('a[href="/admin/overtime"]');
  await expect(leaveNotice).toBeVisible();
  await expect(overtimeNotice).toBeVisible();
  await expect(leaveNotice).not.toContainText("PRIVATE_REASON_SENTINEL");
  await expect(overtimeNotice).not.toContainText("PRIVATE_REASON_SENTINEL");
  await expect(leaveNotice).not.toContainText("EMPLOYEE_IDENTITY_SENTINEL");
  await expect(overtimeNotice).not.toContainText("EMPLOYEE_IDENTITY_SENTINEL");
});
