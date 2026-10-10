import { expect, test } from "@playwright/test";

test("exposes an installable PWA shell", async ({ page, request }) => {
  const browserErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));

  await page.goto("/");

  const headerInstallLink = page.getByRole("link", {
    name: "Tải ứng dụng",
  });
  if (await headerInstallLink.isVisible()) {
    await expect(headerInstallLink).toHaveAttribute("href", "/install");
  } else {
    await page.getByRole("button", { name: "Mở menu" }).click();
    await expect(
      page
        .getByRole("navigation", { name: "Điều hướng di động" })
        .getByRole("link", {
          name: "Tải ứng dụng",
        }),
    ).toHaveAttribute("href", "/install");
  }
  await expect(page.locator('link[rel="manifest"]')).toHaveAttribute(
    "href",
    "/manifest.webmanifest",
  );

  const manifestResponse = await request.get("/manifest.webmanifest");
  expect(manifestResponse.ok()).toBe(true);
  await expect(manifestResponse.json()).resolves.toMatchObject({
    display: "standalone",
    lang: "vi",
    start_url: "/",
  });

  await expect
    .poll(() =>
      page.evaluate(async () =>
        Boolean(await navigator.serviceWorker?.getRegistration("/")),
      ),
    )
    .toBe(true);

  await page.goto("/install");
  const installGuide = page.locator(".install-guide");
  await expect(
    installGuide.getByRole("link", { name: "Xem cách cài trên thiết bị" }),
  ).toBeVisible();
  const nativeInstallAction = installGuide.getByRole("button", {
    name: "Tải ứng dụng",
  });
  if (await nativeInstallAction.isVisible()) {
    await expect(nativeInstallAction).toBeEnabled();
  } else {
    await expect(installGuide).toContainText("menu Chrome hoặc Edge");
  }
  expect(browserErrors).toEqual([]);
});
