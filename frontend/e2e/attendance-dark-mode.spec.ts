import { expect, test } from "@playwright/test";

import { selectWorkspaceTheme } from "./workspace-theme";

test("dark attendance configuration keeps the privacy notice on a dark surface", async ({
  context,
  page,
}) => {
  await context.addCookies([
    {
      name: "cns_access",
      value: "e2e-super-admin-access",
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
      value: "super-admin",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
  await page.goto("/admin/attendance/worksites");
  await selectWorkspaceTheme(page, "Giao diện tối");

  const notice = page.locator("main aside").first();
  await expect(notice).toBeVisible();
  const backgroundLightness = await notice.evaluate((element) => {
    const color = getComputedStyle(element).backgroundColor;
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Canvas context is unavailable.");
    context.fillStyle = color;
    context.fillRect(0, 0, 1, 1);
    const pixels = context.getImageData(0, 0, 1, 1).data;
    const red = pixels[0] ?? 0;
    const green = pixels[1] ?? 0;
    const blue = pixels[2] ?? 0;
    return (red * 0.2126 + green * 0.7152 + blue * 0.0722) / 255;
  });

  expect(backgroundLightness).toBeLessThan(0.25);
});
