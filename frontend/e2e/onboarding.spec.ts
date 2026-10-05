import { expect, test } from "@playwright/test";

test("onboarding stays minimal and keeps OAuth keyboard accessible", async ({
  page,
}) => {
  await page.goto("/register");

  await expect(page.getByRole("radio")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText(
    /(?:REVIEWER|COUNCIL_MEMBER|SUPER_ADMIN|database|schema)/i,
  );

  const googleButton = page.getByRole("button", {
    name: "Tiếp tục với Google",
  });
  await expect(googleButton).toBeVisible();
  const registerButton = page.getByRole("button", { name: "Đăng ký" });
  await registerButton.focus();
  await expect(registerButton).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(googleButton).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(registerButton).toBeFocused();

  expect(
    await page.evaluate(() => document.body.scrollWidth <= window.innerWidth),
  ).toBe(true);
});
