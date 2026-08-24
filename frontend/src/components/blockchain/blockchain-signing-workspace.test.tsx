import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { BlockchainSigningWorkspace } from "@/components/blockchain/blockchain-signing-workspace";

const { queue } = vi.hoisted(() => ({ queue: vi.fn() }));

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  blockchainSigningApi: {
    currentWallet: vi.fn(async () => null),
    queue,
    context: vi.fn(),
    issueWalletChallenge: vi.fn(),
    verifyWalletLink: vi.fn(),
    prepareIntent: vi.fn(),
    submitTransaction: vi.fn(),
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
  it("guides an authorized Super Admin to verify a wallet instead of leaving the signing queue loading", async () => {
    render(<BlockchainSigningWorkspace />, { wrapper: Wrapper });

    expect(
      await screen.findByText("Kết nối và xác minh ví để mở hàng đợi ký."),
    ).toBeDefined();
    expect(queue).not.toHaveBeenCalled();
  });
});
