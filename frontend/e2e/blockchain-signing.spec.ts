import { expect, test } from "@playwright/test";

const walletAddress = "0x3434343434343434343434343434343434343434";
const transactionHash = `0x${"c".repeat(64)}`;

test.beforeEach(async ({ context, page, request }) => {
  await request.post("http://127.0.0.1:4010/api/e2e/reset-blockchain-signing");
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

test("Super Admin sends a THV proof and sees Polygon confirmation progress", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome");
  await page.goto("/blockchain");

  await expect(
    page.getByRole("heading", { level: 1, name: "Hồ sơ chờ ghi nhận" }),
  ).toBeVisible();
  await expect(
    page.getByText("Polygon Mainnet", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Kết nối ví" }).click();
  const verifyWallet = page.getByRole("button", {
    name: "Ký xác minh quyền sở hữu ví",
  });
  if (await verifyWallet.isVisible()) await verifyWallet.click();
  await page
    .getByRole("button", { name: /Hồ sơ đã được duyệt chờ ký/ })
    .click();

  await expect(page.getByRole("list", { name: "Tiến trình ký" })).toContainText(
    "Chuẩn bịChờ MetaMaskĐang xác nhậnĐã ghi nhận",
  );
  await page.getByRole("button", { name: "Ký và ghi nhận blockchain" }).click();

  await expect(
    page.getByText("Giao dịch đã gửi, đang chờ mạng Polygon xác nhận."),
  ).toBeVisible();
  await expect(
    page.getByText("Tài liệu đã được ghi nhận và chưa bị thay đổi."),
  ).toHaveCount(0);
  const confirmedStep = page
    .getByRole("list", { name: "Tiến trình ký" })
    .getByRole("listitem")
    .filter({ hasText: "Đã ghi nhận" });
  await expect(confirmedStep).not.toHaveAttribute("aria-current", "step");
  await expect(confirmedStep).toHaveClass(/border-neutral-200/);
  await expect(
    page.getByRole("link", { name: /Mở giao dịch trên PolygonScan/i }),
  ).toHaveAttribute("href", `https://polygonscan.com/tx/${transactionHash}`);

  await page.getByRole("button", { name: /Sao chép mã giao dịch/i }).click();
  await expect(page.getByText("Đã sao chép mã giao dịch.")).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(
    transactionHash,
  );
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
