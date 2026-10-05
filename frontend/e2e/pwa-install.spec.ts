import { expect, test } from "@playwright/test";

test("exposes an installable PWA shell", async ({ page, request }) => {
  const browserErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));

  await page.goto("/");

  const headerInstallLink = page.getByRole("link", {
    name: "Xem hướng dẫn cài ứng dụng",
  });
  if (await headerInstallLink.isVisible()) {
    await expect(headerInstallLink).toHaveAttribute("href", "/install");
  } else {
    await page.getByRole("button", { name: "Mở menu" }).click();
    await expect(
      page
        .getByRole("navigation", { name: "Điều hướng di động" })
        .getByRole("link", {
          name: "Cài ứng dụng",
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
  expect(browserErrors).toEqual([]);
});
