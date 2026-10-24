import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { AdvertisingCampaignSummary } from "@/lib/api/types";
import { AdvertisingCampaignList } from "./advertising-campaign-list";

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
  creativeTitle: "Bản sắc thương hiệu Trung Nguyên",
  imageUrl: null,
  creativeReviewStatus: "APPROVED",
  creativeReviewNote: null,
  paymentStatus: null,
  deliveryCount: 0,
  createdAt: "2026-10-20T08:00:00Z",
} satisfies AdvertisingCampaignSummary;

describe("AdvertisingCampaignList", () => {
  it("offers a clear first action when the account has no campaigns", async () => {
    const user = userEvent.setup();
    const onCreateCampaign = vi.fn();

    render(
      <AdvertisingCampaignList
        campaigns={[]}
        onCreateCampaign={onCreateCampaign}
        onScheduleCampaign={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Chưa có chiến dịch quảng cáo" }),
    ).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Tạo chiến dịch" }));
    expect(onCreateCampaign).toHaveBeenCalledOnce();
  });

  it("offers booking only after creative approval", async () => {
    const user = userEvent.setup();
    const onScheduleCampaign = vi.fn();

    render(
      <AdvertisingCampaignList
        campaigns={[campaign]}
        onCreateCampaign={vi.fn()}
        onScheduleCampaign={onScheduleCampaign}
      />,
    );

    expect(screen.getByText("Đã duyệt nội dung")).toBeDefined();
    await user.click(
      screen.getByRole("button", { name: "Chọn lịch quảng cáo" }),
    );
    expect(onScheduleCampaign).toHaveBeenCalledWith("campaign-1");
  });

  it("does not offer scheduling while moderation is pending", () => {
    render(
      <AdvertisingCampaignList
        campaigns={[{ ...campaign, status: "PENDING_REVIEW" }]}
        onCreateCampaign={vi.fn()}
        onScheduleCampaign={vi.fn()}
      />,
    );

    expect(screen.getByText("Đang chờ duyệt nội dung")).toBeDefined();
    expect(
      screen.queryByRole("button", { name: "Chọn lịch quảng cáo" }),
    ).toBeNull();
  });

  it("lets an advertiser return to a held booking and finish payment", () => {
    render(
      <AdvertisingCampaignList
        campaigns={[
          {
            ...campaign,
            status: "PENDING_PAYMENT",
            bookingStartAt: "2026-10-25T03:00:00Z",
            paymentStatus: "PENDING",
          },
        ]}
        onCreateCampaign={vi.fn()}
        onScheduleCampaign={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: "Hoàn tất thanh toán" }),
    ).toBeDefined();
  });
});
