import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WalletWithdrawalWorkspace } from "./wallet-withdrawal-workspace";

const { affiliateApi, withdrawalApi } = vi.hoisted(() => ({
  affiliateApi: { me: vi.fn() },
  withdrawalApi: {
    banks: vi.fn(),
    bankAccounts: vi.fn(),
    addBankAccount: vi.fn(),
    setDefaultBankAccount: vi.fn(),
    disableBankAccount: vi.fn(),
    settings: vi.fn(),
    list: vi.fn(),
    create: vi.fn(),
    cancel: vi.fn(),
  },
}));

vi.mock("@/lib/api/client", () => ({ affiliateApi, withdrawalApi }));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => ({ id: "user-1", roles: ["USER"] }),
}));

function renderWorkspace() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <WalletWithdrawalWorkspace />
    </QueryClientProvider>,
  );
}

describe("WalletWithdrawalWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    affiliateApi.me.mockResolvedValue({
      referralCode: "THV-ABC123",
      referralUrl: "https://example.test/r/THV-ABC123",
      status: "ACTIVE",
      clickCount: 0,
      attributedUserCount: 0,
      createdAt: "2026-11-05T00:00:00Z",
      pendingCommissionMinor: 0,
      onHoldCommissionMinor: 0,
      availableBalanceMinor: 25_000,
      reservedBalanceMinor: 0,
      lifetimeEarnedMinor: 25_000,
      totalWithdrawnMinor: 0,
      totalReversedMinor: 0,
    });
    withdrawalApi.banks.mockResolvedValue([
      { bankBin: "970436", bankName: "Vietcombank" },
    ]);
    withdrawalApi.bankAccounts.mockResolvedValue([
      {
        id: "bank-1",
        bankBin: "970436",
        bankName: "Vietcombank",
        accountNumberMasked: "••••6789",
        accountName: "NGUYEN VAN A",
        verificationStatus: "VERIFIED",
        isDefault: true,
        isActive: true,
      },
    ]);
    withdrawalApi.settings.mockResolvedValue({
      enabled: true,
      minimumAmountMinor: 10_000,
      maximumAmountMinor: 100_000_000,
      dailyLimitMinor: 100_000_000,
      dailyCountLimit: 3,
      feeMode: "NONE",
      feeValue: 0,
      manualApprovalRequired: true,
      twoPersonThresholdMinor: null,
      payoutLiveEnabled: false,
    });
    withdrawalApi.list.mockResolvedValue([]);
    withdrawalApi.create.mockResolvedValue({
      id: "withdrawal-1",
      providerReference: "WD-001",
      bankNameSnapshot: "Vietcombank",
      accountNumberMasked: "••••6789",
      amountMinor: 20_000,
      feeMinor: 0,
      netAmountMinor: 20_000,
      status: "PENDING_REVIEW",
      createdAt: "2026-11-05T00:00:00Z",
      approvedAt: null,
      rejectedAt: null,
      succeededAt: null,
      rejectionReason: null,
    });
  });

  it("requests a withdrawal from available commission and shows review status", async () => {
    renderWorkspace();

    expect(await screen.findByText(/25\.000/)).toBeTruthy();
    fireEvent.change(await screen.findByLabelText("Số tiền muốn rút (đồng)"), {
      target: { value: "20000" },
    });
    const submit = screen.getByRole("button", { name: "Gửi yêu cầu rút" });
    expect(submit.hasAttribute("disabled")).toBe(false);
    fireEvent.click(submit);

    await waitFor(() =>
      expect(withdrawalApi.create).toHaveBeenCalledWith(
        "bank-1",
        20_000,
        expect.any(String),
      ),
    );
    expect(await screen.findByText(/Chờ xét duyệt/)).toBeTruthy();
    expect(screen.getAllByText(/không tự động chuyển tiền/).length).toBeGreaterThan(0);
  });

  it("does not allow requests while withdrawals are disabled", async () => {
    withdrawalApi.settings.mockResolvedValue({
      enabled: false,
      minimumAmountMinor: 10_000,
      maximumAmountMinor: 100_000_000,
      dailyLimitMinor: 100_000_000,
      dailyCountLimit: 3,
      feeMode: "NONE",
      feeValue: 0,
      manualApprovalRequired: true,
      twoPersonThresholdMinor: null,
      payoutLiveEnabled: false,
    });
    renderWorkspace();

    expect(await screen.findByText(/chưa được mở/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Gửi yêu cầu rút" })).toBeNull();
  });
});
