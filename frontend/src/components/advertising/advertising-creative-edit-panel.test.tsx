import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AdvertisingCreativeEditPanel } from "./advertising-creative-edit-panel";

const api = vi.hoisted(() => ({
  updateCreative: vi.fn(),
  submitCampaign: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ advertisingApi: api }));

const campaign = {
  id: "campaign-1",
  dossierId: "dossier-1",
  packageId: "package-1",
  placementId: "placement-1",
  placementCode: "FEATURED_DOSSIER",
  placementName: "Hồ sơ nổi bật",
  purchaseContext: "AFTER_PUBLICATION",
  status: "REJECTED",
  desiredStartAt: null,
  actualStartAt: null,
  actualEndAt: null,
  bookingStartAt: null,
  bookingEndAt: null,
  creativeTitle: "Bản sắc thương hiệu",
  creativeDescription: "Mô tả cần cập nhật",
  imageUrl: null,
  destinationUrl: "https://example.test/brand",
  creativeReviewStatus: "CHANGES_REQUESTED",
  creativeReviewNote: "Bổ sung thông tin nguồn gốc.",
  paymentStatus: null,
  deliveryCount: 0,
  createdAt: "2026-10-20T08:00:00Z",
} as const;

describe("AdvertisingCreativeEditPanel", () => {
  it("updates the creative and resubmits it for review", async () => {
    const user = userEvent.setup();
    const onDone = vi.fn();
    api.updateCreative.mockResolvedValue({ id: "creative-2" });
    api.submitCampaign.mockResolvedValue({ status: "PENDING_REVIEW" });
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <AdvertisingCreativeEditPanel
          campaign={campaign}
          onClose={vi.fn()}
          onDone={onDone}
        />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Bổ sung thông tin nguồn gốc.")).toBeDefined();
    await user.clear(screen.getByLabelText("Mô tả nội dung"));
    await user.type(
      screen.getByLabelText("Mô tả nội dung"),
      "Thông tin xuất xứ đã được bổ sung.",
    );
    await user.click(
      screen.getByRole("button", { name: "Lưu nội dung và gửi duyệt" }),
    );

    await waitFor(() =>
      expect(api.updateCreative).toHaveBeenCalledWith(
        "campaign-1",
        expect.objectContaining({
          description: "Thông tin xuất xứ đã được bổ sung.",
        }),
      ),
    );
    expect(api.submitCampaign).toHaveBeenCalledWith("campaign-1");
    expect(onDone).toHaveBeenCalledOnce();
  });
});
