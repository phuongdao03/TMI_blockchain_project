import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AdvertisingCampaignSummary,
  AdvertisingPackage,
  AdvertisingReservationCheckout,
} from "@/lib/api/types";
import { AdvertisingBookingPanel } from "./advertising-booking-panel";

const api = vi.hoisted(() => ({
  availability: vi.fn(),
  quote: vi.fn(),
  reserve: vi.fn(),
  getReservation: vi.fn(),
  joinWaitlist: vi.fn(),
  payOrder: vi.fn(),
  reschedule: vi.fn(),
  walletSummary: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  advertisingApi: api,
  walletApi: { summary: api.walletSummary },
  ApiError: class extends Error {
    constructor(message: string, readonly code = "REQUEST_FAILED") {
      super(message);
    }
  },
}));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => ({ id: "owner-1" }),
}));

const campaign = {
  id: "campaign-1",
  dossierId: "dossier-1",
  packageId: "package-1",
  placementId: "placement-1",
  placementCode: "FEATURED_DOSSIER",
  placementName: "Hồ sơ nổi bật",
  purchaseContext: "AFTER_PUBLICATION",
  status: "APPROVED",
  desiredStartAt: null,
  actualStartAt: null,
  actualEndAt: null,
  bookingStartAt: null,
  bookingEndAt: null,
  creativeTitle: "Bản sắc thương hiệu",
  imageUrl: null,
  creativeReviewStatus: "APPROVED",
  creativeReviewNote: null,
  paymentStatus: null,
  deliveryCount: 0,
  createdAt: "2026-10-20T08:00:00Z",
} satisfies AdvertisingCampaignSummary;

const packageData = {
  id: "package-1",
  code: "FEATURED_DOSSIER_30D",
  name: "Nổi bật 30 ngày",
  placementId: "placement-1",
  durationHours: 720,
  rotationWeight: 1,
  basePriceVnd: 1_390_000,
  priceVersion: 1,
  active: true,
  terms: "",
} satisfies AdvertisingPackage;

const checkout = {
  reservation: {
    id: "reservation-1",
    campaignId: "campaign-1",
    placementId: "placement-1",
    startAt: "2026-10-25T03:00:00Z",
    endAt: "2026-11-24T03:00:00Z",
    expiresAt: "2026-10-24T20:15:00Z",
    status: "HELD",
  },
  order: {
    id: "order-1",
    reservationId: "reservation-1",
    campaignId: "campaign-1",
    membershipTier: "MEMBER",
    membershipCycleStart: null,
    priceVersion: 1,
    discountPolicyVersion: 1,
    baseAmountVnd: 1_390_000,
    discountAmountVnd: 0,
    payableAmountVnd: 1_390_000,
    paymentStatus: "PENDING",
    allowanceExpiresAt: "2026-10-24T20:15:00Z",
    walletTransactionId: null,
    pricingSnapshot: {},
    paidAt: null,
  },
} satisfies AdvertisingReservationCheckout;

function mount(onPaid = vi.fn()) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <AdvertisingBookingPanel
        campaign={campaign}
        packageData={packageData}
        onClose={vi.fn()}
        onPaid={onPaid}
      />
    </QueryClientProvider>,
  );
}

describe("AdvertisingBookingPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    sessionStorage.clear();
    api.availability.mockResolvedValue({
      placement: {
        id: "placement-1",
        code: "FEATURED_DOSSIER",
        name: "Hồ sơ nổi bật",
        pageLocation: "Trang hồ sơ",
        deliveryMode: "WEIGHTED_ROTATION",
        capacity: 3,
        enabled: true,
        timezone: "Asia/Bangkok",
      },
      package: packageData,
      startAt: "2026-10-25T03:00:00Z",
      endAt: "2026-11-24T03:00:00Z",
      available: true,
      remainingSlots: 2,
      alternatives: [],
    });
    api.quote.mockResolvedValue({
      placementCode: "FEATURED_DOSSIER",
      placementName: "Hồ sơ nổi bật",
      packageCode: packageData.code,
      packageName: packageData.name,
      durationHours: 720,
      priceVersion: 1,
      membershipTier: "MEMBER",
      membershipCycleStart: null,
      discountPolicyVersion: 1,
      discountRateBasisPoints: 0,
      remainingDiscountAllowanceVnd: 0,
      baseAmountVnd: 1_390_000,
      discountAmountVnd: 0,
      payableAmountVnd: 1_390_000,
    });
    api.reserve.mockResolvedValue(checkout);
    api.getReservation.mockResolvedValue(checkout);
    api.payOrder.mockResolvedValue({ ...checkout.order, paymentStatus: "PAID" });
    api.walletSummary.mockResolvedValue({ balanceMinor: 5_000_000 });
  });

  it("holds an available slot and waits for payment confirmation before charging", async () => {
    const user = userEvent.setup();
    const onPaid = vi.fn();
    mount(onPaid);

    await user.click(
      await screen.findByRole("button", { name: "Giữ lịch 15 phút" }),
    );
    expect(await screen.findByText(/Giữ chỗ đến/)).toBeDefined();
    expect(api.payOrder).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Thanh toán bằng ví" }));
    await user.click(
      screen.getByRole("button", { name: "Xác nhận trừ ví" }),
    );
    await waitFor(() => expect(api.payOrder).toHaveBeenCalledWith("order-1", expect.any(String)));
    await waitFor(() => expect(onPaid).toHaveBeenCalledOnce());
  });

  it("offers a waitlist when the selected date has no capacity", async () => {
    const user = userEvent.setup();
    api.availability.mockResolvedValueOnce({
      placement: {
        id: "placement-1",
        code: "FEATURED_DOSSIER",
        name: "Hồ sơ nổi bật",
        pageLocation: "Trang hồ sơ",
        deliveryMode: "WEIGHTED_ROTATION",
        capacity: 3,
        enabled: true,
        timezone: "Asia/Bangkok",
      },
      package: packageData,
      startAt: "2026-10-25T03:00:00Z",
      endAt: "2026-11-24T03:00:00Z",
      available: false,
      remainingSlots: 0,
      alternatives: [],
    });
    api.joinWaitlist.mockResolvedValue({ id: "waitlist-1", status: "WAITING" });
    mount();

    await user.click(
      await screen.findByRole("button", { name: "Nhận thông báo khi có chỗ" }),
    );
    expect(api.joinWaitlist).toHaveBeenCalledWith(
      "campaign-1",
      expect.any(String),
    );
    expect(await screen.findByText(/Đã thêm vào danh sách chờ/)).toBeDefined();
  });
});
