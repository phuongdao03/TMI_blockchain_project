import { expect, test } from "@playwright/test";

const walletAddress = "0x3434343434343434343434343434343434343434";
const transactionHash = `0x${"c".repeat(64)}`;

test.beforeEach(async ({ context, page, request }) => {
  await request.post(
    `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}/api/e2e/reset-blockchain-signing`,
  );
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
      name: "cns_csrf",
      value: "e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.addInitScript(
    ({ address, txHash }) => {
      window.ethereum = {
        request: async <T>({ method }: { method: string }) => {
          if (method === "eth_accounts" || method === "eth_requestAccounts") {
            return [address] as T;
          }
          if (method === "eth_chainId") return "0x89" as T;
          if (method === "personal_sign") return `0x${"d".repeat(130)}` as T;
          if (method === "eth_sendTransaction") return txHash as T;
          if (method === "wallet_switchEthereumChain") return null as T;
          throw new Error(`Unsupported E2E wallet method: ${method}`);
        },
        on: () => undefined,
        removeListener: () => undefined,
      };
    },
    { address: walletAddress, txHash: transactionHash },
  );
});

test("authorized staff can record an approved dossier", async ({
  page,
  request,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await page.goto("/blockchain");

  await expect(
    page.getByRole("heading", { level: 1, name: "Hồ sơ chờ ghi nhận" }),
  ).toBeVisible();
  const permissionCheck = page.getByRole("button", {
    name: /^(Xác minh quyền của tổ chức|Kiểm tra quyền xác nhận)$/,
  });
  if (await permissionCheck.isVisible()) await permissionCheck.click();
  await page
    .getByRole("button", { name: /Hồ sơ đã được duyệt chờ ký/ })
    .click();

  const progress = page.getByRole("list", { name: "Tiến trình ký" });
  await expect(progress.getByRole("listitem")).toContainText([
    "Chuẩn bị",
    "Chờ xác nhận",
    "Đang xác nhận",
    "Đã ghi nhận",
  ]);
  await page.getByRole("button", { name: "Xác nhận ghi nhận hồ sơ" }).click();

  await expect(
    page.getByRole("status").getByText(/Yêu cầu đang được xử lý/),
  ).toBeVisible();

  const confirmed = await request.post(
    `http://127.0.0.1:${process.env.E2E_MOCK_PORT ?? "4010"}/api/e2e/confirm-blockchain-signing`,
  );
  expect(confirmed.ok()).toBe(true);
  await expect(
    page.getByRole("button", { name: "Kiểm tra trạng thái" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Kiểm tra trạng thái" }).click();
  await expect(
    page.getByRole("heading", { name: "Hồ sơ đã được ghi nhận" }),
  ).toBeVisible();
  const confirmedStep = progress.getByRole("listitem").filter({
    hasText: "Đã ghi nhận",
  });
  await expect(confirmedStep).toHaveAttribute("aria-current", "step");
  await expect(
    page
      .locator(".blockchain-signing-workspace")
      .getByText(/Polygon|Mainnet|MetaMask|PolygonScan|0x[0-9a-f]{12}/i),
  ).toHaveCount(0);
});

test("blockchain workspace remains visible and usable at 320px", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await page.setViewportSize({ width: 320, height: 844 });
  await page.goto("/blockchain");

  await expect(
    page.getByRole("heading", { level: 1, name: "Hồ sơ chờ ghi nhận" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
});
