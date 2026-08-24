import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context }) => {
  await context.addCookies([
    {
      name: "tmi_access",
      value: "e2e-access",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "tmi_refresh",
      value: "e2e-refresh",
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
      httpOnly: false,
      sameSite: "Lax",
    },
    {
      name: "tmi_e2e_persona",
      value: "applicant",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
});

test("dark mode keeps applicant dashboard surfaces and labels readable", async ({
  page,
}) => {
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Giao diện tối" }).click();

  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const metrics = page.getByRole("region", { name: "Chỉ số tổng quan" });
  await expect(metrics).not.toHaveCSS("background-color", "rgb(255, 255, 255)");
  await expect(metrics).not.toHaveCSS("background-color", "rgb(251, 250, 247)");
  await expect(metrics.getByText("Việc cần làm")).toBeVisible();
});
