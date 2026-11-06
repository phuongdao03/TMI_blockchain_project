import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminWithdrawalsWorkspace } from "./admin-withdrawals-workspace";

const { adminFinanceApi, adminWithdrawalApi, withdrawalApi, auth } = vi.hoisted(
  () => ({
    adminFinanceApi: {
      reconciliation: vi.fn(),
      saveBank: vi.fn(),
      updateSettings: vi.fn(),
    },
    adminWithdrawalApi: {
      list: vi.fn(),
      detail: vi.fn(),
      approve: vi.fn(),
      dispatchPayout: vi.fn(),
      verifyBank: vi.fn(),
      reviewIdentity: vi.fn(),
      reject: vi.fn(),
    },
    withdrawalApi: { settings: vi.fn(), banks: vi.fn() },
    auth: {
      user: {
        id: "admin-1",
        roles: ["SUPER_ADMIN"],
        permissions: ["finance.read", "finance.withdrawals.approve"],
      },
    },
  }),
);

vi.mock("@/lib/api/client", () => ({
  adminFinanceApi,
  adminWithdrawalApi,
  withdrawalApi,
}));
vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => auth.user }));

function renderWorkspace() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <AdminWithdrawalsWorkspace />
    </QueryClientProvider>,
  );
}

describe("AdminWithdrawalsWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    withdrawalApi.banks.mockResolvedValue([
      { bankBin: "970436", bankName: "Vietcombank" },
    ]);
    adminFinanceApi.reconciliation.mockResolvedValue({
      checkedJournals: 10,
      unbalancedJournals: 0,
      unbalancedJournalIds: [],
      checkedReservedAccounts: 3,
      reservedBalanceMismatches: [],
      payoutExceptions: [],
    });
    adminWithdrawalApi.list.mockResolvedValue([
      {
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
      },
    ]);
    adminWithdrawalApi.detail.mockResolvedValue({
      id: "withdrawal-1",
      providerReference: "WD-001",
      bankNameSnapshot: "Vietcombank",
      bankBinSnapshot: "970436",
      accountNumberMasked: "••••6789",
      accountNumber: "0123456789",
      accountName: "NGUYEN VAN A",
      userId: "user-1",
      amountMinor: 20_000,
      feeMinor: 0,
      netAmountMinor: 20_000,
      status: "PENDING_REVIEW",
      createdAt: "2026-11-05T00:00:00Z",
      approvedAt: null,
      rejectedAt: null,
      succeededAt: null,
      rejectionReason: null,
      approvals: [],
      events: [],
      payoutAttempts: [],
    });
    adminWithdrawalApi.approve.mockResolvedValue({
      id: "withdrawal-1",
      status: "APPROVED",
    });
    adminWithdrawalApi.dispatchPayout.mockResolvedValue({
      id: "withdrawal-1",
      status: "QUEUED",
    });
    adminWithdrawalApi.reject.mockResolvedValue({
      id: "withdrawal-1",
      status: "REJECTED",
    });
  });

  it("reviews a withdrawal without describing approval as a payout", async () => {
    renderWorkspace();

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Xem chi tiết yêu cầu WD-001",
      }),
    );
    expect(await screen.findByText("0123456789")).toBeTruthy();
    expect(screen.getByText(/không tự động chuyển tiền/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Ghi nhận phê duyệt" }));

    await waitFor(() =>
      expect(adminWithdrawalApi.approve).toHaveBeenCalledWith(
        "withdrawal-1",
        expect.any(Object),
      ),
    );
  });

  it("requires a reason before rejecting", async () => {
    renderWorkspace();
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Xem chi tiết yêu cầu WD-001",
      }),
    );
    expect(await screen.findByText("0123456789")).toBeTruthy();
    expect(
      screen
        .getByRole("button", { name: "Từ chối yêu cầu" })
        .hasAttribute("disabled"),
    ).toBe(true);
    fireEvent.change(screen.getByLabelText(/Lý do từ chối/), {
      target: { value: "Thông tin ngân hàng chưa khớp" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Từ chối yêu cầu" }));
    await waitFor(() =>
      expect(adminWithdrawalApi.reject).toHaveBeenCalledWith(
        "withdrawal-1",
        "Thông tin ngân hàng chưa khớp",
      ),
    );
  });

  it("requires explicit confirmation and live gates before payout dispatch", async () => {
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
      payoutLiveEnabled: true,
    });
    adminWithdrawalApi.list.mockResolvedValue([
      {
        id: "withdrawal-1",
        providerReference: "WD-001",
        bankNameSnapshot: "Vietcombank",
        accountNumberMasked: "••••6789",
        amountMinor: 20_000,
        feeMinor: 0,
        netAmountMinor: 20_000,
        status: "APPROVED",
        createdAt: "2026-11-05T00:00:00Z",
        approvedAt: "2026-11-05T00:01:00Z",
        rejectedAt: null,
        succeededAt: null,
        rejectionReason: null,
      },
    ]);
    adminWithdrawalApi.detail.mockResolvedValue({
      id: "withdrawal-1",
      providerReference: "WD-001",
      bankNameSnapshot: "Vietcombank",
      bankBinSnapshot: "970436",
      accountNumberMasked: "••••6789",
      accountNumber: "0123456789",
      accountName: "NGUYEN VAN A",
      userId: "user-1",
      amountMinor: 20_000,
      feeMinor: 0,
      netAmountMinor: 20_000,
      status: "APPROVED",
      createdAt: "2026-11-05T00:00:00Z",
      approvedAt: "2026-11-05T00:01:00Z",
      rejectedAt: null,
      succeededAt: null,
      rejectionReason: null,
      approvals: [],
      events: [],
      payoutAttempts: [],
    });
    renderWorkspace();
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Xem chi tiết yêu cầu WD-001",
      }),
    );
    await screen.findByText("0123456789");
    const queueButton = screen.getByRole("button", {
      name: "Gửi lệnh chi trả",
    });
    expect(queueButton.hasAttribute("disabled")).toBe(true);
    fireEvent.click(screen.getByLabelText(/Tôi đã đối chiếu người nhận/));
    fireEvent.click(queueButton);
    await waitFor(() =>
      expect(adminWithdrawalApi.dispatchPayout).toHaveBeenCalledWith(
        "withdrawal-1",
        expect.any(Object),
      ),
    );
  });
});
