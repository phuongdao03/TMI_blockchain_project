import { expect, test } from "@playwright/test";
import { selectWorkspaceTheme } from "./workspace-theme";

test.beforeEach(async ({ context, page }) => {
  await context.addCookies(
    (
      [
        ["cns_access", "e2e-access"],
        ["cns_refresh", "e2e-refresh"],
        ["cns_csrf", "e2e-csrf"],
      ] as const
    ).map(([name, value]) => ({
      name,
      value,
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax" as const,
    })),
  );
  await page.emulateMedia({ reducedMotion: "reduce" });
});

test("member chat uses a room rail and a focused mobile conversation", async ({
  page,
}, info) => {
  const envelope = (data: unknown) => ({ success: true, data });
  await page.route("**/api/v1/community/chat/*/access", (route) =>
    route.fulfill({ json: envelope({ allowed: true, source: "TIER" }) }),
  );
  await page.route("**/api/v1/community/chat/*/messages*", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        json: envelope({
          id: "sent-demo",
          displayName: "Bạn",
          tier: "PRESTIGE",
          body: route.request().postDataJSON().body,
          createdAt: "2026-10-27T09:00:00Z",
          editedAt: null,
          canEdit: true,
          canRemove: true,
          isAdmin: false,
        }),
      });
    } else
      await route.fulfill({
        json: envelope({
          items: [
            {
              id: "welcome",
              displayName: "Lan Anh",
              tier: "COMPANION",
              body: "Chào mọi người, cùng chia sẻ câu chuyện làng nghề nhé!",
              createdAt: "2026-10-27T08:00:00Z",
              editedAt: null,
              isAdmin: false,
              canEdit: false,
              canRemove: false,
            },
          ],
          hasMore: false,
          nextCursor: null,
        }),
      });
  });
  await page.goto("/membership?room=COMPANION");
  const chat = page.locator("#community-chat");
  await expect(
    chat.getByText("Chào mọi người, cùng chia sẻ câu chuyện làng nghề nhé!"),
  ).toBeVisible();
  for (const theme of ["Giao diện sáng", "Giao diện tối"] as const) {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await selectWorkspaceTheme(page, theme);
    for (const width of [390, 768, 1440]) {
      await page.setViewportSize({ width, height: 950 });
      await chat.scrollIntoViewIfNeeded();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
      ).toBe(true);
      await chat.screenshot({
        path: `../docs/ux-evidence-2026-10-27/chat-redesign-${theme === "Giao diện sáng" ? "light" : "dark"}-${width}-${info.project.name}.png`,
      });
    }
  }
  await chat
    .getByRole("textbox", { name: /Tin nhắn/ })
    .fill("Lời chào từ phòng hội viên");
  await chat.getByRole("button", { name: "Gửi tin nhắn" }).click();
  await expect(
    chat.getByText("Lời chào từ phòng hội viên", { exact: true }),
  ).toBeVisible();
});

test("requested labels and GPS actions remain readable", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: "Xem quy trình", exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("Xem quy trình và chi phí", { exact: true }),
  ).toHaveCount(0);
  await page.goto("/verify/demo-token");
  const title = page
    .locator(".verification-panel dd")
    .filter({ hasText: "Video chào mừng" });
  await expect(title).toBeVisible();
  await expect(title).toHaveCSS("word-break", "normal");
  await context.addCookies([
    {
      name: "cns_e2e_persona",
      value: "super-admin",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);
  await page.goto("/admin/attendance/worksites");
  await page
    .getByText("GPS · Cấu hình vùng chấm công", { exact: true })
    .click();
  const create = page.getByRole("button", {
    name: "Tạo phiên bản mới",
    exact: true,
  });
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 950 });
    await expect(create).toHaveCSS("white-space", "nowrap");
    expect(
      await create.evaluate(
        (button) => button.scrollWidth <= button.clientWidth + 1,
      ),
    ).toBe(true);
  }
});
