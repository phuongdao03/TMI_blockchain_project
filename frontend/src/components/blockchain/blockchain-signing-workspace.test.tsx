import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BlockchainSigningWorkspace } from "@/components/blockchain/blockchain-signing-workspace";
import { readPendingProofBroadcast } from "@/lib/blockchain/pending-proof-broadcast";

const {
  connectBrowserWallet,
  currentBrowserWallet,
  currentWallet,
  issueWalletChallenge,
  verifyWalletLink,
  signBrowserChallenge,
  prepareIntent,
  proofQueue,
  sendBrowserTransaction,
  submitTransaction,
  transactionStatus,
  MockApiError,
  walletOptionsMock,
  injectedMetaMaskMock,
} = vi.hoisted(() => ({
  connectBrowserWallet: vi.fn(),
  currentBrowserWallet: vi.fn(),
  connectWalletWithConnector: vi.fn(),
  currentWallet: vi.fn(),
  issueWalletChallenge: vi.fn(),
  verifyWalletLink: vi.fn(),
  signBrowserChallenge: vi.fn(),
  prepareIntent: vi.fn(),
  proofQueue: vi.fn(),
  sendBrowserTransaction: vi.fn(),
  submitTransaction: vi.fn(),
  transactionStatus: vi.fn(),
  walletOptionsMock: vi.fn(() => [] as { id: string; name: string }[]),
  injectedMetaMaskMock: vi.fn(() => false),
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
    issueWalletChallenge,
    verifyWalletLink,
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
  currentWallet: currentBrowserWallet,
  sendTransaction: sendBrowserTransaction,
  signWalletChallenge: signBrowserChallenge,
  subscribeWalletChanges: vi.fn(() => () => undefined),
  switchChain: vi.fn(),
  walletOptions: walletOptionsMock,
  hasInjectedMetaMask: injectedMetaMaskMock,
  walletAddressesMatch: (expected?: string | null, actual?: string | null) =>
    Boolean(
      expected && actual && expected.toLowerCase() === actual.toLowerCase(),
    ),
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
    walletOptionsMock.mockReturnValue([]);
    injectedMetaMaskMock.mockReturnValue(false);
    window.localStorage.clear();
    currentWallet.mockResolvedValue(null);
    issueWalletChallenge.mockResolvedValue({
      id: "challenge-1",
      nonce: "challenge-nonce",
      message: "THV wallet verification",
    });
    signBrowserChallenge.mockResolvedValue("0xsignature");
    verifyWalletLink.mockResolvedValue({
      id: "wallet-link",
      walletAddress: "0x3434343434343434343434343434343434",
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    currentBrowserWallet.mockResolvedValue({ address: null, chainId: 137 });
    proofQueue.mockResolvedValue([]);
    connectBrowserWallet.mockResolvedValue({
      address: "0x3434343434343434343434343434343434343434",
      chainId: 137,
    });
    transactionStatus.mockImplementation(() => new Promise(() => undefined));
  });

  it("restores an already connected browser wallet after a reload", async () => {
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: "0x3434343434343434343434343434343434343434",
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    currentBrowserWallet.mockResolvedValue({
      address: "0x3434343434343434343434343434343434343434",
      chainId: 137,
    });

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    expect(
      await screen.findByText("Ứng dụng xác nhận đã kết nối"),
    ).toBeDefined();
    expect(currentBrowserWallet).toHaveBeenCalledOnce();
  });

  it("checks an authorized wallet on production without sending a transaction", async () => {
    const address = "0x3434343434343434343434343434343434";
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: address,
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    currentBrowserWallet.mockResolvedValue({ address, chainId: 137 });
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    await userEvent.setup().click(
      await screen.findByRole("button", {
        name: "Kiểm tra quyền xác nhận",
      }),
    );

    await waitFor(() =>
      expect(verifyWalletLink).toHaveBeenCalledWith({
        challengeId: "challenge-1",
        nonce: "challenge-nonce",
        signature: "0xsignature",
      }),
    );
    expect(issueWalletChallenge).toHaveBeenCalledWith(address, 137);
    expect(signBrowserChallenge).toHaveBeenCalledWith(
      "THV wallet verification",
      address,
    );
    expect(
      await screen.findByText(/Đã kiểm tra quyền xác nhận thành công/),
    ).toBeDefined();
    expect(prepareIntent).not.toHaveBeenCalled();
    expect(sendBrowserTransaction).not.toHaveBeenCalled();
  });

  it("explains a revoked contract signer role during a safe wallet check", async () => {
    const address = "0x3434343434343434343434343434343434343434";
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: address,
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    currentBrowserWallet.mockResolvedValue({ address, chainId: 137 });
    verifyWalletLink.mockRejectedValue(
      new MockApiError("Forbidden", "BLOCKCHAIN_FORBIDDEN", 403),
    );
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    await userEvent.setup().click(
      await screen.findByRole("button", {
        name: "Kiểm tra quyền xác nhận",
      }),
    );

    expect(
      (
        await screen.findByText(
          "Ứng dụng xác nhận chưa được cấp quyền cho thao tác này. Hãy liên hệ quản trị viên.",
        )
      ).closest('[role="alert"]'),
    ).not.toBeNull();
    expect(sendBrowserTransaction).not.toHaveBeenCalled();
  });

  it("clears a failed connection notice after MetaMask finishes connecting", async () => {
    connectBrowserWallet.mockRejectedValue(
      Object.assign(new Error("User rejected the request"), { code: 4001 }),
    );
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await userEvent.setup().click(
      await screen.findByRole("button", {
        name: "Kết nối ứng dụng xác nhận",
      }),
    );
    expect(
      await screen.findByText(/Bạn chưa chấp thuận kết nối/),
    ).toBeDefined();

    currentBrowserWallet.mockResolvedValue({
      address: "0x3434343434343434343434343434343434",
      chainId: 137,
    });
    act(() => window.dispatchEvent(new Event("focus")));
    await waitFor(() => {
      expect(screen.queryByText(/Bạn chưa chấp thuận kết nối/)).toBeNull();
      expect(screen.getByText("Ứng dụng xác nhận đã kết nối")).toBeDefined();
    });
  });

  it("treats a wallet as connected when MetaMask grants access despite a request error", async () => {
    connectBrowserWallet.mockRejectedValue(
      new Error("Provider request failed"),
    );
    currentBrowserWallet.mockResolvedValue({
      address: "0x3434343434343434343434343434343434",
      chainId: 137,
    });
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    await userEvent
      .setup()
      .click(await screen.findByRole("button", { name: "Làm mới kết nối" }));

    expect(
      await screen.findByText("Ứng dụng xác nhận đã kết nối"),
    ).toBeDefined();
    expect(screen.queryByText(/Chưa thể kết nối ứng dụng xác nhận/)).toBeNull();
  });

  it("accepts checksum casing differences for the authorized wallet", async () => {
    const user = userEvent.setup();
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: "0xBfA38182f0D24589e7898DD4892C58c3FDa58042",
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    currentBrowserWallet.mockResolvedValue({
      address: "0xbfa38182f0d24589e7898dd4892c58c3fda58042",
      chainId: 137,
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: null,
        dossierId: "dossier-case",
        dossierCode: "THV-2026-CASE",
        dossierTitle: "Tác phẩm chờ ký",
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
    await user.click(
      await screen.findByRole("button", { name: /Tác phẩm chờ ký/ }),
    );

    expect(screen.queryByText(/ví|blockchain|Polygon/i)).toBeNull();
    expect(
      screen
        .getByRole("button", { name: "Xác nhận ghi nhận hồ sơ" })
        .hasAttribute("disabled"),
    ).toBe(false);
  });

  it("lets an operator reopen MetaMask when an intent is still SIGNING without a transaction hash", async () => {
    const user = userEvent.setup();
    const walletAddress = "0x3434343434343434343434343434343434343434";
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress,
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    currentBrowserWallet.mockResolvedValue({
      address: walletAddress,
      chainId: 137,
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: "transaction-signing",
        dossierId: "dossier-signing",
        dossierCode: "THV-2026-SIGNING",
        dossierTitle: "Hồ sơ đang chờ ví",
        version: 2,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "SIGNING",
        txHash: null,
        confirmations: 0,
        errorCode: null,
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);
    prepareIntent.mockResolvedValue({
      intentId: "intent-signing",
      transactionId: "transaction-signing",
      dossierId: "dossier-signing",
      dossierCode: "THV-2026-SIGNING",
      dossierTitle: "Hồ sơ đang chờ ví",
      version: 2,
      assetId: `0x${"11".repeat(32)}`,
      proofHash: `0x${"ab".repeat(32)}`,
      network: "polygon-mainnet",
      chainId: 137,
      contractAddress: "0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F",
      transactionRequest: {
        to: "0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F",
      },
      estimatedGas: 100000,
      gasPriceWei: 30000000000,
      walletBalanceWei: 1000000000000000000,
      expiresAt: "2026-08-26T00:10:00Z",
    });
    sendBrowserTransaction.mockRejectedValue(
      Object.assign(new Error("User rejected the request"), { code: 4001 }),
    );

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await user.click(
      await screen.findByRole("button", { name: /Hồ sơ đang chờ ví/ }),
    );

    expect(
      screen.getByText(
        "Chưa nhận được xác nhận. Bạn có thể mở lại ứng dụng để tiếp tục.",
      ),
    ).toBeDefined();
    const retryButton = screen.getByRole("button", {
      name: "Mở lại ứng dụng để tiếp tục",
    });
    expect(retryButton.hasAttribute("disabled")).toBe(false);

    await user.click(retryButton);
    expect(prepareIntent).toHaveBeenCalledWith(
      "dossier-signing",
      2,
      walletAddress,
    );
    expect(sendBrowserTransaction).toHaveBeenCalledOnce();
  });

  it("recovers an already-mined proof after prepare returns a conflict", async () => {
    const user = userEvent.setup();
    const walletAddress = "0x3434343434343434343434343434343434343434";
    const transactionHash = `0x${"91".repeat(32)}`;
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress,
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    currentBrowserWallet.mockResolvedValue({
      address: walletAddress,
      chainId: 137,
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: "transaction-recovery",
        dossierId: "dossier-recovery",
        dossierCode: "THV-2026-RECOVERY",
        dossierTitle: "Proof awaiting wallet recovery",
        version: 1,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "SIGNING",
        txHash: null,
        confirmations: 0,
        errorCode: null,
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);
    transactionStatus
      .mockImplementationOnce(() => new Promise(() => undefined))
      .mockResolvedValue({
        transactionId: "transaction-recovery",
        status: "CONFIRMED",
        txHash: transactionHash,
        confirmations: 24,
        errorCode: null,
        errorMessage: null,
        confirmedAt: "2026-08-26T00:01:00Z",
      });
    prepareIntent.mockRejectedValue(
      new MockApiError("Proof already exists.", "BLOCKCHAIN_CONFLICT", 409),
    );

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await user.click(
      await screen.findByRole("button", {
        name: /Proof awaiting wallet recovery/,
      }),
    );
    await user.click(
      screen.getByRole("button", { name: "Mở lại ứng dụng để tiếp tục" }),
    );

    expect(await screen.findByText("Hồ sơ đã được ghi nhận")).toBeDefined();
    expect(screen.queryByText(transactionHash)).toBeNull();
    expect(sendBrowserTransaction).not.toHaveBeenCalled();
  });

  it("shows a pending status after the user confirms a record", async () => {
    const user = userEvent.setup();
    const walletAddress = "0x3434343434343434343434343434343434343434";
    const transactionHash = `0x${"cd".repeat(32)}`;
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress,
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    currentBrowserWallet.mockResolvedValue({
      address: walletAddress,
      chainId: 137,
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: null,
        dossierId: "dossier-ready",
        dossierCode: "THV-2026-READY",
        dossierTitle: "Hồ sơ sẵn sàng ký",
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
      intentId: "intent-ready",
      transactionId: "transaction-ready",
      dossierId: "dossier-ready",
      dossierCode: "THV-2026-READY",
      dossierTitle: "Hồ sơ sẵn sàng ký",
      version: 1,
      assetId: `0x${"11".repeat(32)}`,
      proofHash: `0x${"ab".repeat(32)}`,
      network: "polygon-mainnet",
      chainId: 137,
      contractAddress: "0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F",
      transactionRequest: {
        to: "0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F",
      },
      estimatedGas: 100000,
      gasPriceWei: 30000000000,
      walletBalanceWei: 1000000000000000000,
      expiresAt: "2026-08-26T00:10:00Z",
    });
    sendBrowserTransaction.mockResolvedValue(transactionHash);
    submitTransaction.mockImplementation(() => new Promise(() => undefined));
    transactionStatus.mockResolvedValue({
      transactionId: "transaction-ready",
      status: "SIGNING",
      txHash: null,
      confirmations: 0,
      errorCode: null,
    });

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await user.click(
      await screen.findByRole("button", { name: /Hồ sơ sẵn sàng ký/ }),
    );
    await user.click(
      screen.getByRole("button", { name: "Xác nhận ghi nhận hồ sơ" }),
    );

    expect(
      await screen.findByText(
        "Yêu cầu đã được gửi. Hệ thống đang cập nhật trạng thái.",
      ),
    ).toBeDefined();
    expect(screen.queryByText(transactionHash)).toBeNull();
    expect(screen.getByText("Đang xử lý")).toBeDefined();
    expect(screen.queryByText(/Polygon|MetaMask|blockchain/i)).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Mở lại ứng dụng để tiếp tục" }),
    ).toBeNull();
    expect(submitTransaction).toHaveBeenCalledWith({
      transactionId: "transaction-ready",
      intentId: "intent-ready",
      transactionHash,
      connectedWallet: walletAddress,
    });
  });

  it("does not open two wallet signing flows after rapid activation", async () => {
    const user = userEvent.setup();
    const walletAddress = "0x3434343434343434343434343434343434";
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress,
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    currentBrowserWallet.mockResolvedValue({
      address: walletAddress,
      chainId: 137,
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: null,
        dossierId: "dossier-rapid",
        dossierCode: "THV-2026-RAPID",
        dossierTitle: "Hồ sơ ký nhanh",
        version: 1,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "CREATED",
        txHash: null,
        confirmations: 0,
        errorCode: null,
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);
    prepareIntent.mockImplementation(() => new Promise(() => undefined));

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await user.click(
      await screen.findByRole("button", { name: /Hồ sơ ký nhanh/ }),
    );
    const button = screen.getByRole("button", {
      name: "Xác nhận ghi nhận hồ sơ",
    });
    act(() => {
      button.click();
      button.click();
    });
    expect(prepareIntent).toHaveBeenCalledOnce();
    expect(sendBrowserTransaction).not.toHaveBeenCalled();
  });

  it("resubmits a wallet hash saved before a page reload without asking MetaMask again", async () => {
    const user = userEvent.setup();
    const walletAddress = `0x${"34".repeat(20)}`;
    const transactionHash = `0x${"77".repeat(32)}`;
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress,
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    currentBrowserWallet.mockResolvedValue({
      address: walletAddress,
      chainId: 137,
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: "transaction-reload",
        dossierId: "dossier-reload",
        dossierCode: "THV-2026-RELOAD",
        dossierTitle: "Hồ sơ cần đồng bộ",
        version: 1,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "SIGNING",
        txHash: null,
        confirmations: 0,
        errorCode: null,
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);
    window.localStorage.setItem(
      "thv-proof-broadcast:dossier-reload:1",
      JSON.stringify({
        dossierId: "dossier-reload",
        version: 1,
        transactionId: "transaction-reload",
        intentId: "intent-reload",
        transactionHash,
        connectedWallet: walletAddress,
      }),
    );
    expect(
      readPendingProofBroadcast("dossier-reload", 1)?.transactionHash,
    ).toBe(transactionHash);
    submitTransaction
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue({
        transactionId: "transaction-reload",
        status: "BROADCAST",
        txHash: transactionHash,
        confirmations: 0,
        errorCode: null,
      });
    transactionStatus.mockRejectedValue(new Error("offline"));

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await user.click(
      await screen.findByRole("button", { name: /Hồ sơ cần đồng bộ/ }),
    );

    expect(screen.queryByText(transactionHash)).toBeNull();
    await waitFor(() => expect(submitTransaction).toHaveBeenCalledOnce());
    expect(
      await screen.findByText(
        "Chưa thể cập nhật trạng thái. Yêu cầu đã được gửi; hãy thử lại khi có kết nối.",
      ),
    ).toBeDefined();
    expect(window.localStorage.length).toBe(1);
    await user.click(screen.getByRole("button", { name: "Tiếp tục kiểm tra" }));
    expect(
      await screen.findByText(
        "Đã nhận yêu cầu xác nhận. Hệ thống đang cập nhật trạng thái.",
      ),
    ).toBeDefined();
    expect(submitTransaction).toHaveBeenCalledWith({
      transactionId: "transaction-reload",
      intentId: "intent-reload",
      transactionHash,
      connectedWallet: walletAddress,
    });
    expect(sendBrowserTransaction).not.toHaveBeenCalled();
    expect(window.localStorage.length).toBe(0);
  });

  it("guides an authorized Super Admin to verify a wallet instead of leaving the signing queue loading", async () => {
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    expect(
      await screen.findByText(
        "Kết nối ứng dụng xác nhận để xem hồ sơ đủ điều kiện.",
      ),
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

  it("explains the confirmation flow and exposes a four-step journey", async () => {
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

    expect(screen.getByText("Quyền xác nhận của tổ chức")).toBeDefined();
    expect(screen.queryByText(/Polygon|blockchain|dấu vân tay số/i)).toBeNull();
    expect(
      screen.getByRole("button", { name: "Xác nhận ghi nhận hồ sơ" }),
    ).toBeDefined();
    const stepper = screen.getByRole("list", { name: "Tiến trình ký" });
    expect(within(stepper).getAllByRole("listitem")).toHaveLength(4);
    expect(within(stepper).getByText("Chuẩn bị")).toBeDefined();
    expect(within(stepper).getByText("Chờ xác nhận")).toBeDefined();
    expect(within(stepper).getByText("Đang xác nhận")).toBeDefined();
    expect(within(stepper).getByText("Đã ghi nhận")).toBeDefined();
  });

  it("shows the completed state only after confirmation", async () => {
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
    expect(screen.getByText("Hồ sơ đã được ghi nhận")).toBeDefined();
    expect(
      screen.getByText(/Bản ghi giúp đối chiếu mã hồ sơ và phiên bản/i),
    ).toBeDefined();
    expect(screen.queryByText(transactionHash)).toBeNull();
    expect(
      screen.queryByText(/Polygon|blockchain|dấu vân tay|chữ ký/i),
    ).toBeNull();
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
      screen.getByText(
        "Yêu cầu đang được xử lý. Trạng thái sẽ cập nhật sau khi hoàn tất.",
      ),
    ).toBeDefined();
    expect(
      screen.queryByText("Tài liệu đã được ghi nhận và chưa bị thay đổi."),
    ).toBeNull();
  });

  it("rechecks a failed transaction with a hash and shows its recovered confirmation", async () => {
    const user = userEvent.setup();
    const transactionHash = `0x${"ef".repeat(32)}`;
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: "0x3434343434343434343434343434343434343434",
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: "transaction-recoverable",
        dossierId: "dossier-1",
        dossierCode: "THV-2026-001",
        dossierTitle: "Tác phẩm cần đối chiếu",
        version: 2,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "FAILED",
        txHash: transactionHash,
        confirmations: 0,
        errorCode: "CHAIN_REORG",
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);
    transactionStatus.mockResolvedValue({
      transactionId: "transaction-recoverable",
      status: "CONFIRMED",
      txHash: transactionHash,
      confirmations: 12,
      errorCode: null,
      confirmedAt: "2026-08-26T00:01:00Z",
    });

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await user.click(
      await screen.findByRole("button", { name: /Tác phẩm cần đối chiếu/ }),
    );

    expect(await screen.findByText("Hồ sơ đã được ghi nhận")).toBeDefined();
    expect(transactionStatus).toHaveBeenCalledWith("transaction-recoverable");
  });

  it("offers a retry when the status cannot be updated", async () => {
    const user = userEvent.setup();
    const transactionHash = `0x${"ef".repeat(32)}`;
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: "0x3434343434343434343434343434343434343434",
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: "transaction-unavailable",
        dossierId: "dossier-1",
        dossierCode: "THV-2026-001",
        dossierTitle: "Tác phẩm đang xác nhận",
        version: 2,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "BROADCAST",
        txHash: transactionHash,
        confirmations: 0,
        errorCode: null,
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);
    transactionStatus.mockRejectedValue(
      new MockApiError(
        "Proof registry is unavailable.",
        "BLOCKCHAIN_UNAVAILABLE",
        503,
      ),
    );

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await user.click(
      await screen.findByRole("button", { name: /Tác phẩm đang xác nhận/ }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Chưa nhận được kết quả xác nhận",
      }),
    ).toBeDefined();
    expect(screen.queryByText(transactionHash)).toBeNull();
    expect(
      screen.getByRole("button", { name: "Thử kiểm tra lại" }),
    ).toBeDefined();
  });

  it("shows a failed receipt as an actionable result instead of endless confirmation", async () => {
    const user = userEvent.setup();
    const transactionHash = `0x${"ef".repeat(32)}`;
    currentWallet.mockResolvedValue({
      id: "wallet-link",
      walletAddress: "0x3434343434343434343434343434343434343434",
      chainId: 137,
      status: "ACTIVE",
      verifiedAt: "2026-08-26T00:00:00Z",
    });
    proofQueue.mockResolvedValue([
      {
        transactionId: "transaction-failed",
        dossierId: "dossier-1",
        dossierCode: "THV-2026-001",
        dossierTitle: "Tác phẩm cần kiểm tra",
        version: 2,
        proofHash: `0x${"ab".repeat(32)}`,
        status: "FAILED",
        txHash: transactionHash,
        confirmations: 0,
        errorCode: "TRANSACTION_MISMATCH",
        createdAt: "2026-08-26T00:00:00Z",
      },
    ]);
    transactionStatus.mockResolvedValue({
      transactionId: "transaction-failed",
      status: "FAILED",
      txHash: transactionHash,
      confirmations: 0,
      errorCode: "TRANSACTION_MISMATCH",
      confirmedAt: null,
    });

    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });
    await user.click(
      await screen.findByRole("button", { name: /Tác phẩm cần kiểm tra/ }),
    );

    expect(
      (await screen.findAllByText("Cần kiểm tra trạng thái")).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByText("Đang đối chiếu giao dịch")).toBeNull();
    const stepper = screen.getByRole("list", { name: "Tiến trình ký" });
    expect(stepper.querySelector(".auth-activity-spinner")).toBeNull();
    expect(within(stepper).getByText("Cần kiểm tra")).toBeDefined();
    expect(screen.getByText(/Hồ sơ đang được kiểm tra/i)).toBeDefined();
    expect(
      screen.getByRole("button", { name: "Kiểm tra trạng thái" }),
    ).toBeDefined();
  });

  it("explains when the user rejects a wallet connection", async () => {
    const user = userEvent.setup();
    connectBrowserWallet.mockRejectedValue(
      Object.assign(new Error("User rejected the request"), { code: 4001 }),
    );
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    await user.click(
      await screen.findByRole("button", {
        name: "Kết nối ứng dụng xác nhận",
      }),
    );

    expect(
      await screen.findByText(
        "Bạn chưa chấp thuận kết nối. Hãy chọn Kết nối để thử lại.",
      ),
    ).toBeDefined();
  });

  it("opens the installed MetaMask directly even when other connectors exist", async () => {
    walletOptionsMock.mockReturnValue([
      { id: "metamask", name: "MetaMask" },
      { id: "walletconnect", name: "WalletConnect" },
    ]);
    injectedMetaMaskMock.mockReturnValue(true);
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    await userEvent.setup().click(
      await screen.findByRole("button", {
        name: "Kết nối ứng dụng xác nhận",
      }),
    );

    await waitFor(() => expect(connectBrowserWallet).toHaveBeenCalledOnce());
    expect(
      screen.queryByRole("dialog", { name: "Chọn ứng dụng xác nhận" }),
    ).toBeNull();
  });

  it.each([
    {
      address: "0x3434343434343434343434343434343434343434",
      chainId: 1,
      expected: "Ứng dụng xác nhận chưa sẵn sàng",
    },
    {
      address: "0x5656565656565656565656565656565656565656",
      chainId: 137,
      expected: "Ứng dụng xác nhận chưa sẵn sàng",
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
        await screen.findByRole("button", {
          name: "Kết nối ứng dụng xác nhận",
        }),
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

    await user.click(
      await screen.findByRole("button", {
        name: "Kết nối ứng dụng xác nhận",
      }),
    );
    await user.click(
      await screen.findByRole("button", { name: /Hồ sơ cần gas/ }),
    );
    await user.click(
      screen.getByRole("button", { name: "Xác nhận ghi nhận hồ sơ" }),
    );

    expect(
      await screen.findByText(
        "Chưa thể hoàn tất xác nhận. Hãy liên hệ bộ phận hỗ trợ để được kiểm tra.",
      ),
    ).toBeDefined();
    expect(sendBrowserTransaction).toHaveBeenCalledWith(
      expect.objectContaining({
        from: "0x3434343434343434343434343434343434343434",
      }),
    );
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
