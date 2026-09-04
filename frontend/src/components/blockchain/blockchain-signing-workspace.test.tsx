import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BlockchainSigningWorkspace } from "@/components/blockchain/blockchain-signing-workspace";

const {
  connectBrowserWallet,
  currentWallet,
  prepareIntent,
  proofQueue,
  sendBrowserTransaction,
  submitTransaction,
  transactionStatus,
  MockApiError,
} = vi.hoisted(() => ({
  connectBrowserWallet: vi.fn(),
  connectWalletWithConnector: vi.fn(),
  currentWallet: vi.fn(),
  prepareIntent: vi.fn(),
  proofQueue: vi.fn(),
  sendBrowserTransaction: vi.fn(),
  submitTransaction: vi.fn(),
  transactionStatus: vi.fn(),
  MockApiError: class MockApiError extends Error {
    constructor(
      message: string,
      readonly code: string,
      readonly status: number,
    ) {
      super(message);
    }
  },
}));

vi.mock("@/lib/api/client", () => ({
  ApiError: MockApiError,
  walletLinkApi: {
    currentWallet,
    issueWalletChallenge: vi.fn(),
    verifyWalletLink: vi.fn(),
  },
  proofRegistrySigningApi: {
    queue: proofQueue,
    prepareIntent,
    submitTransaction,
    status: transactionStatus,
  },
}));

vi.mock("@/lib/blockchain/eip1193", () => ({
  connectWallet: connectBrowserWallet,
  connectWalletWithConnector: vi.fn(),
  currentWallet: vi.fn(),
  sendTransaction: sendBrowserTransaction,
  signWalletChallenge: vi.fn(),
  subscribeWalletChanges: vi.fn(() => () => undefined),
  switchChain: vi.fn(),
  walletOptions: vi.fn(() => []),
  walletErrorCode: (error: { code?: number | string; message?: string }) => {
    if (error?.code === 4001) return "USER_REJECTED";
    if (error?.code === -32002) return "REQUEST_PENDING";
    if (error?.code === 4100) return "UNAUTHORIZED";
    if (error?.code === 4900) return "DISCONNECTED";
    if (error?.code === 4901) return "CHAIN_UNAVAILABLE";
    if (error?.message?.toLowerCase().includes("not found")) return "NO_WALLET";
    return "WALLET_ERROR";
  },
}));

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {children}
    </QueryClientProvider>
  );
}

describe("BlockchainSigningWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentWallet.mockResolvedValue(null);
    proofQueue.mockResolvedValue([]);
    connectBrowserWallet.mockResolvedValue({
      address: "0x3434343434343434343434343434343434343434",
      chainId: 137,
    });
    transactionStatus.mockImplementation(() => new Promise(() => undefined));
  });

  it("guides an authorized Super Admin to verify a wallet instead of leaving the signing queue loading", async () => {
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    expect(
      await screen.findByText("Kết nối và xác minh ví để mở hàng đợi ký."),
    ).toBeDefined();
    expect(proofQueue).not.toHaveBeenCalled();
    expect(screen.queryByText("Kiểm soát an toàn")).toBeNull();
    expect(screen.queryByText(/private key|seed phrase/i)).toBeNull();
    expect(
      screen.queryByText(/THVProofRegistry|VERIFIER_ROLE|Chain ID/i),
    ).toBeNull();
  });

  it("does not expose a provider error to internal users", async () => {
    currentWallet.mockRejectedValue(
      new Error("Unable to find any account for 60"),
    );
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    expect(
      await screen.findByText(/khu vực ghi nhận đang tạm gián đoạn/i),
    ).toBeDefined();
    expect(screen.queryByText(/Unable to find any account/i)).toBeNull();
    expect(screen.queryByText(/RPC|ABI|allowlist|contract/i)).toBeNull();
  });

  it("loads approved dossiers from THVProofRegistry instead of CertificateRegistry", async () => {
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: "0x3434343434343434343434343434343434343434",
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: null,
        dossierId: "dossier-1",
        dossierCode: "THV-2026-001",
        dossierTitle: "Tác phẩm đã duyệt",
        version: 1,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "CREATED",
        txHash: null,
        confirmations: 0,
        errorCode: null,
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    expect(await screen.findByText("Tác phẩm đã duyệt")).toBeDefined();
    expect(proofQueue).toHaveBeenCalledOnce();
  });

  it("explains the Polygon proof flow and exposes a four-step signing journey", async () => {
    const user = userEvent.setup();
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: "0x3434343434343434343434343434343434343434",
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: null,
        dossierId: "dossier-1",
        dossierCode: "THV-2026-001",
        dossierTitle: "Tác phẩm đã duyệt",
        version: 2,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "CREATED",
        txHash: null,
        confirmations: 0,
        errorCode: null,
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await user.click(await screen.findByRole("button", { name: /Tác phẩm/ }));

    expect(screen.getAllByText("Polygon Mainnet").length).toBeGreaterThan(0);
    expect(screen.getByText("Dấu vân tay số của hồ sơ")).toBeDefined();
    expect(
      screen.getByRole("button", { name: "Ký và ghi nhận blockchain" }),
    ).toBeDefined();
    const stepper = screen.getByRole("list", { name: "Tiến trình ký" });
    expect(within(stepper).getAllByRole("listitem")).toHaveLength(4);
    expect(within(stepper).getByText("Chuẩn bị")).toBeDefined();
    expect(within(stepper).getByText("Chờ MetaMask")).toBeDefined();
    expect(within(stepper).getByText("Đang xác nhận")).toBeDefined();
    expect(within(stepper).getByText("Đã ghi nhận")).toBeDefined();
  });

  it("shows confirmed language only for backend CONFIRMED and supports transaction actions", async () => {
    const user = userEvent.setup();
    const transactionHash = `0x${"cd".repeat(32)}`;
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: "0x3434343434343434343434343434343434343434",
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: "transaction-1",
        dossierId: "dossier-1",
        dossierCode: "THV-2026-001",
        dossierTitle: "Tác phẩm đã ghi nhận",
        version: 2,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "CONFIRMED",
        txHash: transactionHash,
        confirmations: 12,
        errorCode: null,
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await user.click(
      await screen.findByRole("button", { name: /Tác phẩm đã ghi nhận/ }),
    );

    expect(
      screen.getByText("Tài liệu đã được ghi nhận và chưa bị thay đổi."),
    ).toBeDefined();
    const explorerLink = screen.getByRole("link", {
      name: "Mở giao dịch trên PolygonScan",
    });
    expect(explorerLink.getAttribute("href")).toBe(
      `https://polygonscan.com/tx/${transactionHash}`,
    );

    await user.click(
      screen.getByRole("button", { name: "Sao chép mã giao dịch" }),
    );
    expect(await navigator.clipboard.readText()).toBe(transactionHash);
    expect(screen.getByText("Đã sao chép mã giao dịch.")).toBeDefined();
  });

  it("keeps a broadcast transaction in the pending state", async () => {
    const user = userEvent.setup();
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: "0x3434343434343434343434343434343434343434",
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: "transaction-pending",
        dossierId: "dossier-1",
        dossierCode: "THV-2026-001",
        dossierTitle: "Tác phẩm đang chờ",
        version: 2,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "BROADCAST",
        txHash: `0x${"ef".repeat(32)}`,
        confirmations: 0,
        errorCode: null,
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await user.click(
      await screen.findByRole("button", { name: /Tác phẩm đang chờ/ }),
    );

    expect(
      screen.getByText("Giao dịch đã gửi, đang chờ mạng Polygon xác nhận."),
    ).toBeDefined();
    expect(
      screen.queryByText("Tài liệu đã được ghi nhận và chưa bị thay đổi."),
    ).toBeNull();
  });

  it("explains when the user rejects MetaMask", async () => {
    const user = userEvent.setup();
    connectBrowserWallet.mockRejectedValue(
      Object.assign(new Error("User rejected the request"), { code: 4001 }),
    );
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    await user.click(await screen.findByRole("button", { name: "Kết nối ví" }));

    expect(
      await screen.findByText(
        "Bạn đã từ chối yêu cầu ký trong MetaMask. Giao dịch chưa được gửi.",
      ),
    ).toBeDefined();
  });

  it.each([
    {
      address: "0x3434343434343434343434343434343434343434",
      chainId: 1,
      expected: "Sai mạng blockchain",
    },
    {
      address: "0x5656565656565656565656565656565656565656",
      chainId: 137,
      expected: "Sai tài khoản ví",
    },
  ])(
    "blocks signing when MetaMask reports $expected",
    async (browserWallet) => {
      const user = userEvent.setup();
      currentWallet.mockResolvedValue({
        id: "wallet-link",
        walletAddress: "0x3434343434343434343434343434343434343434",
        chainId: 137,
        status: "ACTIVE",
        verifiedAt: "2026-08-26T00:00:00Z",
      });
      connectBrowserWallet.mockResolvedValue(browserWallet);
      render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

      await user.click(
        await screen.findByRole("button", { name: "Kết nối ví" }),
      );

      expect(await screen.findByText(browserWallet.expected)).toBeDefined();
    },
  );

  it("explains an insufficient gas balance without marking the proof confirmed", async () => {
    const user = userEvent.setup();
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: "0x3434343434343434343434343434343434343434",
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: null,
        dossierId: "dossier-gas",
        dossierCode: "THV-2026-GAS",
        dossierTitle: "Hồ sơ cần gas",
        version: 1,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "CREATED",
        txHash: null,
        confirmations: 0,
        errorCode: null,
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);
    prepareIntent.mockResolvedValue({
      intentId: "intent-gas",
      transactionId: "transaction-gas",
      dossierId: "dossier-gas",
      dossierCode: "THV-2026-GAS",
      dossierTitle: "Hồ sơ cần gas",
      version: 1,
      assetId: `0x${"11".repeat(32)}`,
      proofHash: `0x${"ab".repeat(32)}`,
      network: "polygon-mainnet",
      chainId: 137,
      contractAddress: "0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F",
      transactionRequest: { to: "0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F" },
      estimatedGas: 100000,
      gasPriceWei: 30000000000,
      walletBalanceWei: 0,
      expiresAt: "2026-08-26T00:10:00Z",
    });
    sendBrowserTransaction.mockRejectedValue(
      Object.assign(new Error("insufficient funds for gas"), { code: -32000 }),
    );
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    await user.click(await screen.findByRole("button", { name: "Kết nối ví" }));
    await user.click(
      await screen.findByRole("button", { name: /Hồ sơ cần gas/ }),
    );
    await user.click(
      screen.getByRole("button", { name: "Ký và ghi nhận blockchain" }),
    );

    expect(
      await screen.findByText(
        "Ví không đủ MATIC để trả phí gas. Hãy nạp thêm MATIC rồi thử lại.",
      ),
    ).toBeDefined();
    expect(submitTransaction).not.toHaveBeenCalled();
    expect(
      screen.queryByText("Tài liệu đã được ghi nhận và chưa bị thay đổi."),
    ).toBeNull();
  });

  it("explains a service interruption without technical implementation details", async () => {
    currentWallet.mockRejectedValue(
      new MockApiError(
        "Blockchain service is unavailable.",
        "BLOCKCHAIN_UNAVAILABLE",
        503,
      ),
    );

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    expect(
      await screen.findByRole("heading", {
        name: "Chưa thể mở khu vực ghi nhận",
      }),
    ).toBeDefined();
    expect(screen.queryByText(/RPC|ABI|allowlist|contract|mã lỗi/i)).toBeNull();
  });

  it("shows the permission guidance only for an actual forbidden response", async () => {
    currentWallet.mockRejectedValue(
      new MockApiError(
        "Blockchain administration access is forbidden.",
        "BLOCKCHAIN_FORBIDDEN",
        403,
      ),
    );

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    expect(
      await screen.findByRole("heading", {
        name: "Tài khoản chưa được phân quyền",
      }),
    ).toBeDefined();
    expect(screen.queryByText(/BLOCKCHAIN_FORBIDDEN|mã lỗi/i)).toBeNull();
  });
});
