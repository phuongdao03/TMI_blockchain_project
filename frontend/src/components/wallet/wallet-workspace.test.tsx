import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WalletWorkspace } from "./wallet-workspace";

const { api, auth } = vi.hoisted(() => ({
  api: {
    summary: vi.fn(),
    topup: vi.fn(),
    reconcile: vi.fn(),
    resume: vi.fn(),
  },
  auth: { user: null as { id: string; roles: string[] } | null },
}));

vi.mock("@/lib/api/client", () => ({ walletApi: api }));
vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => auth.user }));

const summary = {
  balanceMinor: 0,
  currency: "VND" as const,
  provider: "payos",
  transactions: [],
  topups: [],
};

function renderWorkspace() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <WalletWorkspace />
    </QueryClientProvider>,
  );
}

describe("WalletWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.user = { id: "member-1", roles: ["USER"] };
    api.summary.mockResolvedValue(summary);
  });

  it("shows the payment QR and bank details inside the wallet page", async () => {
    api.topup.mockResolvedValue({
      id: "topup-1",
      orderCode: "123456",
      amountMinor: 10_000,
      status: "PENDING",
      checkoutUrl: "https://payos.example/checkout",
      qrPayload: "payos-qr-payload",
      bankBin: "970436",
      bankAccountNumber: "0123456789",
      bankAccountName: "TINH HOA VIET",
      transferDescription: "THV 123456",
      createdAt: "2026-10-26T00:00:00Z",
      expiresAt: "2026-10-26T01:00:00Z",
      paidAt: null,
    });

    renderWorkspace();
    fireEvent.change(await screen.findByLabelText("Số tiền (VNĐ)"), {
      target: { value: "10000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Nạp tiền" }));

    expect(
      await screen.findByRole("heading", {
        name: /Quét mã để nạp/,
      }),
    ).toBeTruthy();
    expect(screen.getByRole("img", { name: /Mã QR thanh toán/ })).toBeTruthy();
    expect(screen.getByText("TINH HOA VIET")).toBeTruthy();
    expect(screen.getByText("0123456789")).toBeTruthy();
    expect(screen.getByText("THV 123456")).toBeTruthy();
    expect(
      screen.queryByRole("link", { name: /PayOS|Mở cổng|Tiếp tục nạp/ }),
    ).toBeNull();
  });

  it("does not offer wallet top-ups to a super admin", async () => {
    auth.user = { id: "admin-1", roles: ["SUPER_ADMIN"] };

    renderWorkspace();

    expect(await screen.findByText("Ví quản trị")).toBeTruthy();
    expect(screen.queryByLabelText("Số tiền (VNĐ)")).toBeNull();
    expect(screen.queryByRole("button", { name: "Nạp tiền" })).toBeNull();
  });
});
