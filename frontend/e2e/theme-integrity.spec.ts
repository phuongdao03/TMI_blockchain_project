import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context }) => {
  await context.addCookies([
    {
      name: "tmi_access",
      value: "e2e-super-admin-access",
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
  ]);
});

test("operations surfaces switch cleanly between light and dark themes", async ({
  page,
}) => {
  await page.goto("/admin/content");
  await page.getByRole("button", { name: "Giao diện tối" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  const editor = page.locator(".cms-workspace").locator("section").first();
  const darkBackground = await editor.evaluate(
    (element) => getComputedStyle(element).backgroundColor,
  );
  expect(darkBackground).not.toBe("rgb(255, 255, 255)");

  await page.getByRole("button", { name: "Giao diện sáng" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  const lightBackground = await editor.evaluate(
    (element) => getComputedStyle(element).backgroundColor,
  );
  expect(lightBackground).toBe("rgb(255, 255, 255)");
});
