import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdvertisingAdminWorkspace } from "./advertising-admin-workspace";

const api = vi.hoisted(() => ({
  reviewQueue: vi.fn(),
  placements: vi.fn(),
  reviewCampaign: vi.fn(),
  pauseCampaign: vi.fn(),
  adminInventory: vi.fn(),
  reports: vi.fn(),
  packages: vi.fn(),
  createPlacement: vi.fn(),
  updatePlacement: vi.fn(),
  createPackage: vi.fn(),
  updatePackage: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ advertisingApi: api }));
vi.mock("@/components/wallet/wallet-workspace", () => ({
  formatVnd: (value: number) => `${value.toLocaleString("vi-VN")} ₫`,
}));

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AdvertisingAdminWorkspace />
    </QueryClientProvider>,
  );
}

describe("AdvertisingAdminWorkspace", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.reviewQueue.mockResolvedValue([
      {
        campaignId: "campaign-1",
        ownerEmail: "owner@example.test",
        dossierId: "dossier-1",
        dossierCode: "CNS-2026-123456",
        dossierTitle: "Hồ sơ nhận diện thương hiệu",
        placementCode: "FEATURED_DOSSIER",
        packageName: "Nổi bật 30 ngày",
        campaignStatus: "PENDING_REVIEW",
        creativeId: "creative-1",
        creativeVersion: 1,
        title: "Câu chuyện thương hiệu",
        description: "Thông tin giới thiệu thương hiệu Việt.",
        imageUrl: null,
        destinationUrl: "https://example.test/brand",
        reviewStatus: "PENDING",
      },
    ]);
    api.placements.mockResolvedValue([]);
    api.reviewCampaign.mockResolvedValue({ status: "APPROVED" });
  });

  it("shows a submitted creative and confirms before approving it", async () => {
    const user = userEvent.setup();
    mount();

    expect(
      await screen.findByRole(
        "heading",
        { name: "Câu chuyện thương hiệu" },
        { timeout: 5_000 },
      ),
    ).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Duyệt nội dung" }));
    expect(screen.getByRole("dialog")).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Duyệt chiến dịch" }));

    await waitFor(() =>
      expect(api.reviewCampaign).toHaveBeenCalledWith("campaign-1", "APPROVE", undefined),
    );
  });
});
