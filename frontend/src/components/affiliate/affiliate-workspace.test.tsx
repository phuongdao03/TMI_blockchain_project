import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AffiliateWorkspace } from "./affiliate-workspace";

const affiliateApi = vi.hoisted(() => ({
  me: vi.fn(),
  referrals: vi.fn(),
  commissions: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ affiliateApi }));
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
      <AffiliateWorkspace />
    </QueryClientProvider>,
  );
}

describe("AffiliateWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    affiliateApi.me.mockResolvedValue({
      referralCode: "THV-ABC123",
      referralUrl: "https://example.test/r/THV-ABC123",
      status: "ACTIVE",
      clickCount: 12,
      attributedUserCount: 4,
      createdAt: "2026-11-01T00:00:00Z",
      pendingCommissionMinor: 5_000,
      onHoldCommissionMinor: 3_000,
      availableBalanceMinor: 25_000,
      reservedBalanceMinor: 2_000,
      lifetimeEarnedMinor: 49_000,
      totalWithdrawnMinor: 10_000,
      totalReversedMinor: 0,
    });
    affiliateApi.referrals.mockResolvedValue([
      {
        id: "ref-1",
        attributedAt: "2026-11-01T00:00:00Z",
        expiresAt: "2026-12-01T00:00:00Z",
        conversionCount: 2,
        revenueMinor: 50_000,
        commissionAmountMinor: 5_000,
      },
    ]);
    affiliateApi.commissions.mockResolvedValue([
      {
        id: "commission-1",
        serviceCode: "MEMBERSHIP",
        commissionAmountMinor: 25_000,
        status: "AVAILABLE",
        earnedAt: "2026-11-02T00:00:00Z",
      },
    ]);
  });

  it("shows referral metrics and commission history", async () => {
    renderWorkspace();

    expect(await screen.findByText("THV-ABC123")).toBeTruthy();
    expect(screen.getByText("12")).toBeTruthy();
    expect(screen.getByText("4")).toBeTruthy();
    expect(await screen.findByText(/49\.000/)).toBeTruthy();
    expect(await screen.findByText("Gói thành viên")).toBeTruthy();
    expect(await screen.findByText("Người được giới thiệu")).toBeTruthy();
    expect(screen.getByText("50.000 ₫")).toBeTruthy();
    expect(
      screen.getByDisplayValue("https://example.test/?ref=THV-ABC123"),
    ).toBeTruthy();
  });
});
