import { expect, test } from "@playwright/test";

test("onboarding exposes safe account intents and keyboard-accessible OAuth", async ({
  page,
}) => {
  await page.goto("/register");

  await expect(
    page.getByRole("radio", { name: /Khám phá công khai/i }),
  ).toBeVisible();
  await expect(page.getByRole("radio", { name: /Cá nhân/i })).toBeVisible();
  await expect(page.getByRole("radio", { name: /Tổ chức/i })).toBeVisible();

  const googleButton = page.getByRole("button", {
    name: "Tiếp tục với Google",
  });
  await expect(googleButton).toBeVisible();
  await googleButton.focus();
  await expect(googleButton).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("textbox", { name: "Email" })).toBeFocused();

  expect(
    await page.evaluate(() => document.body.scrollWidth <= window.innerWidth),
  ).toBe(true);
});
