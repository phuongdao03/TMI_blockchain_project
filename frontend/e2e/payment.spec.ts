import { expect, test } from "@playwright/test";

test.beforeEach(async ({ context, request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-payment");
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
      name: "tmi_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
});

test("approved dossier creates order and waits for trusted paid status", async ({
  page,
}) => {
  const consoleIssues: string[] = [];
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleIssues.push(`${message.type()}: ${message.text()}`);
    }
  });

  await page.goto("/ho-so/9155dbf5-bb3e-449d-8bf0-9572cc642cac");
  await page.getByRole("button", { name: "Tạo lệnh thanh toán" }).click();
  await expect(page).toHaveURL(/\/thanh-toan\/a255dbf5-/);
  await expect(
    page.getByRole("heading", { name: "Thanh toán thành công" }),
  ).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("Biên nhận đã được xác thực")).toBeVisible();
  await expect(page.getByText(/1\.000\.000/)).toBeVisible();
  expect(consoleIssues).toEqual([]);
});
