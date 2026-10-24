import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdvertisingSetupPanel } from "./advertising-setup-panel";

const api = vi.hoisted(() => ({
  campaigns: vi.fn(),
  placements: vi.fn(),
  packages: vi.fn(),
  quote: vi.fn(),
  createCampaign: vi.fn(),
  submitCampaign: vi.fn(),
  listDossiers: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  advertisingApi: api,
  dossierApi: { list: api.listDossiers },
}));

const dossier = {
  id: "dossier-1",
  code: "CNS-2026-123456",
  ownerUserId: "owner-1",
  organizationId: null,
  categoryId: "category-1",
  dossierTypeId: null,
  dossierTypeVersionId: null,
  formData: {},
  title: "Hồ sơ nhận diện thương hiệu",
  slug: null,
  summary: "Tư liệu chính thức về thương hiệu.",
  status: "PUBLISHED",
  visibility: "PUBLIC",
  currentVersionNo: 1,
  submittedAt: "2026-10-01T00:00:00Z",
  createdAt: "2026-09-01T00:00:00Z",
  updatedAt: "2026-10-01T00:00:00Z",
  canEdit: false,
};

function mount(onCreated = vi.fn()) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <AdvertisingSetupPanel onCreated={onCreated} />
    </QueryClientProvider>,
  );
}

describe("AdvertisingSetupPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.listDossiers.mockResolvedValue({ data: [dossier] });
    api.placements.mockResolvedValue([
      {
        id: "placement-1",
        code: "FEATURED_DOSSIER",
        name: "Hồ sơ nổi bật",
        pageLocation: "Trang hồ sơ",
        deliveryMode: "WEIGHTED_ROTATION",
        capacity: 3,
        enabled: true,
        timezone: "Asia/Bangkok",
      },
    ]);
    api.packages.mockResolvedValue([
      {
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
      },
    ]);
    api.quote.mockResolvedValue({
      placementCode: "FEATURED_DOSSIER",
      placementName: "Hồ sơ nổi bật",
      packageCode: "FEATURED_DOSSIER_30D",
      packageName: "Nổi bật 30 ngày",
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
    api.createCampaign.mockResolvedValue({
      campaign: { id: "campaign-1" },
      creativeId: "creative-1",
    });
    api.submitCampaign.mockResolvedValue({ id: "campaign-1" });
  });

  it("creates and submits a campaign using the selected dossier and package", async () => {
    const user = userEvent.setup();
    const onCreated = vi.fn();
    mount(onCreated);

    expect(await screen.findAllByText("1.390.000 ₫")).toHaveLength(2);
    await user.type(
      screen.getByRole("textbox", { name: "Tên nội dung quảng cáo" }),
      "Bản sắc thương hiệu",
    );
    await user.type(
      screen.getByRole("textbox", { name: "Mô tả ngắn" }),
      "Câu chuyện và tư liệu đã xác thực.",
    );
    await user.type(
      screen.getByRole("textbox", { name: "Liên kết đích" }),
      "/cong-dong",
    );
    await user.click(
      screen.getByRole("button", { name: "Tạo chiến dịch và gửi duyệt" }),
    );

    await waitFor(() => expect(api.createCampaign).toHaveBeenCalledOnce());
    expect(api.createCampaign).toHaveBeenCalledWith({
      dossierId: "dossier-1",
      packageCode: "FEATURED_DOSSIER_30D",
      title: "Bản sắc thương hiệu",
      description: "Câu chuyện và tư liệu đã xác thực.",
      imageUrl: null,
      destinationUrl: "/cong-dong",
    });
    expect(api.submitCampaign).toHaveBeenCalledWith("campaign-1");
    await waitFor(() => expect(onCreated).toHaveBeenCalledOnce());
  });
});
