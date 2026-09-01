import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BlockchainSigningWorkspace } from "@/components/blockchain/blockchain-signing-workspace";

const { currentWallet, legacyQueue, proofQueue, MockApiError } = vi.hoisted(
  () => ({
    currentWallet: vi.fn(),
    legacyQueue: vi.fn(),
    proofQueue: vi.fn(),
    MockApiError: class MockApiError extends Error {
      constructor(
        message: string,
        readonly code: string,
        readonly status: number,
      ) {
        super(message);
      }
    },
  }),
);

vi.mock("@/lib/api/client", () => ({
  ApiError: MockApiError,
  blockchainSigningApi: {
    currentWallet,
    queue: legacyQueue,
    context: vi.fn(),
    issueWalletChallenge: vi.fn(),
    verifyWalletLink: vi.fn(),
    prepareIntent: vi.fn(),
    submitTransaction: vi.fn(),
  },
  proofRegistrySigningApi: {
    queue: proofQueue,
    prepareIntent: vi.fn(),
    submitTransaction: vi.fn(),
    status: vi.fn(),
  },
}));

vi.mock("@/lib/blockchain/eip1193", () => ({
  connectWallet: vi.fn(),
  currentWallet: vi.fn(),
  sendTransaction: vi.fn(),
  signWalletChallenge: vi.fn(),
  subscribeWalletChanges: vi.fn(() => () => undefined),
  switchChain: vi.fn(),
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
  });

  it("guides an authorized Super Admin to verify a wallet instead of leaving the signing queue loading", async () => {
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    expect(
      await screen.findByText("Kết nối và xác minh ví để mở hàng đợi ký."),
    ).toBeDefined();
    expect(proofQueue).not.toHaveBeenCalled();
    expect(legacyQueue).not.toHaveBeenCalled();
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
    expect(legacyQueue).not.toHaveBeenCalled();
  });

  it("distinguishes a blockchain configuration failure from missing admin access", async () => {
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
        name: "Dịch vụ blockchain chưa sẵn sàng",
      }),
    ).toBeDefined();
    expect(screen.queryByText(/Chỉ Super Admin được ký blockchain/)).toBeNull();
    expect(screen.getByText("Mã lỗi: BLOCKCHAIN_UNAVAILABLE")).toBeDefined();
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
        name: "Chưa có quyền ký blockchain",
      }),
    ).toBeDefined();
    expect(screen.getByText("Mã lỗi: BLOCKCHAIN_FORBIDDEN")).toBeDefined();
  });
});
