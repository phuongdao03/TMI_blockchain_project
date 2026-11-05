import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminAffiliateWorkspace } from "./admin-affiliate-workspace";

const { adminAffiliateApi } = vi.hoisted(() => ({
  adminAffiliateApi: {
    profiles: vi.fn(),
    profileReferrals: vi.fn(),
    suspend: vi.fn(),
    restore: vi.fn(),
    commissions: vi.fn(),
    approveCommission: vi.fn(),
    rejectCommission: vi.fn(),
    reverseCommission: vi.fn(),
    commissionRules: vi.fn(),
    createCommissionRules: vi.fn(),
    publishCommissionRules: vi.fn(),
  },
}));

vi.mock("@/lib/api/client", () => ({ adminAffiliateApi }));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => ({
    id: "admin-1",
    roles: ["MODERATOR"],
    permissions: [
      "affiliate.profiles.manage",
      "affiliate.commissions.approve",
      "affiliate.rules.manage",
    ],
  }),
}));

function renderWorkspace() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <AdminAffiliateWorkspace />
    </QueryClientProvider>,
  );
}

describe("AdminAffiliateWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    adminAffiliateApi.profiles.mockResolvedValue([
      {
        userId: "affiliate-user-1",
        referralCode: "THV-ABC123",
        status: "ACTIVE",
        createdAt: "2026-11-01T00:00:00Z",
        clickCount: 12,
        attributedUserCount: 4,
      },
    ]);
    adminAffiliateApi.suspend.mockResolvedValue({ status: "SUSPENDED" });
    adminAffiliateApi.restore.mockResolvedValue({ status: "ACTIVE" });
    adminAffiliateApi.profileReferrals.mockResolvedValue([
      {
        id: "referral-1",
        attributedAt: "2026-11-02T00:00:00Z",
        expiresAt: "2026-12-02T00:00:00Z",
        conversionCount: 2,
        revenueMinor: 40_000,
        commissionAmountMinor: 4_000,
      },
    ]);
    adminAffiliateApi.commissions.mockResolvedValue([
      {
        id: "commission-1",
        affiliateUserId: "affiliate-user-1",
        referredUserId: "referred-user-1",
        ruleSetVersion: 1,
        serviceCode: "MEMBERSHIP",
        sourceReference: "membership-order-1",
        amountMinor: 50_000,
        commissionAmountMinor: 5_000,
        rateBasisPoints: 1_000,
        currency: "VND",
        status: "PENDING",
        earnedAt: "2026-11-02T00:00:00Z",
        holdUntil: "2026-12-02T00:00:00Z",
        approvedAt: null,
        reviewedByUserId: null,
        reviewReason: null,
        reversedAt: null,
        reversalReason: null,
        createdAt: "2026-11-02T00:00:00Z",
      },
    ]);
    adminAffiliateApi.approveCommission.mockResolvedValue({ status: "ON_HOLD" });
    adminAffiliateApi.rejectCommission.mockResolvedValue({ status: "REJECTED" });
    adminAffiliateApi.reverseCommission.mockResolvedValue({ status: "REVERSED" });
    adminAffiliateApi.commissionRules.mockResolvedValue([
      {
        id: "rule-1",
        versionNo: 1,
        status: "DRAFT",
        enabled: false,
        attributionWindowDays: 30,
        holdDays: 30,
        level2Enabled: false,
        level2RateBasisPoints: 0,
        effectiveFrom: null,
        publishedAt: null,
        publishedByUserId: null,
        rates: [{ serviceCode: "MEMBERSHIP", directRateBasisPoints: 500 }],
      },
    ]);
    adminAffiliateApi.createCommissionRules.mockResolvedValue({ id: "rule-2" });
    adminAffiliateApi.publishCommissionRules.mockResolvedValue({ status: "PUBLISHED" });
  });

  it("suspends an affiliate only after a reason is supplied", async () => {
    renderWorkspace();

    expect(await screen.findByText("THV-ABC123")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tạm ngưng hồ sơ" }));
    fireEvent.change(screen.getByLabelText(/Lý do thay đổi trạng thái/), {
      target: { value: "Confirmed policy abuse" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận tạm ngưng" }));

    await waitFor(() => {
      expect(adminAffiliateApi.suspend).toHaveBeenCalledWith(
        "affiliate-user-1",
        "Confirmed policy abuse",
      );
    });
  });

  it("loads privacy-safe referral history when a profile is expanded", async () => {
    renderWorkspace();

    expect(await screen.findByText("THV-ABC123")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Xem lịch sử giới thiệu" }));

    await waitFor(() => {
      expect(adminAffiliateApi.profileReferrals).toHaveBeenCalledWith(
        "affiliate-user-1",
      );
    });
    expect(await screen.findByText("Lượt giới thiệu")).toBeTruthy();
    expect(screen.getByText("40.000 ₫")).toBeTruthy();
    expect(screen.queryByText("referred-user-1")).toBeNull();
  });

  it("reviews pending commissions and manages draft rule sets", async () => {
    renderWorkspace();

    fireEvent.click(await screen.findByRole("button", { name: "Phê duyệt" }));
    await waitFor(() => {
      expect(adminAffiliateApi.approveCommission.mock.calls[0]?.[0]).toBe("commission-1");
    });

    fireEvent.change(screen.getByLabelText("Dịch vụ"), {
      target: { value: "ADVERTISING" },
    });
    fireEvent.change(screen.getByLabelText("Tỷ lệ hoa hồng (%)"), {
      target: { value: "3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Tạo bản nháp" }));
    await waitFor(() => {
      expect(adminAffiliateApi.createCommissionRules.mock.calls[0]?.[0]).toEqual({
        enabled: false,
        attributionWindowDays: 30,
        holdDays: 30,
        rates: [{ serviceCode: "ADVERTISING", directRateBasisPoints: 300 }],
      });
    });

    fireEvent.click(await screen.findByRole("button", { name: "Phát hành phiên bản" }));
    await waitFor(() => {
      expect(adminAffiliateApi.publishCommissionRules.mock.calls[0]?.[0]).toBe("rule-1");
    });
  });
});
