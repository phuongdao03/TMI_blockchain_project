import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { VotingParticipantWorkspace } from "@/components/admin/voting-participant-workspace";
import { publicApi, votingCampaignAdminApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  publicApi: { search: vi.fn() },
  votingCampaignAdminApi: {
    list: vi.fn(),
    participants: vi.fn(),
    bulkAdd: vi.fn(),
    transition: vi.fn(),
  },
}));

const campaign = {
  id: "campaign-1",
  name: "Bình chọn tháng tám",
  slug: "thang-tam",
  description: "Chiến dịch cộng đồng",
  status: "DRAFT" as const,
  campaignType: "PERIODIC" as const,
  periodType: "MONTHLY" as const,
  timezone: "Asia/Ho_Chi_Minh",
  startAt: "2026-08-05T00:00:00Z",
  endAt: "2026-09-05T00:00:00Z",
  maxVotesPerUser: 3,
  maxVotesPerWorkPerUser: 1,
  allowVoteChange: true,
  allowVoteRevoke: true,
  requireVerifiedEmail: true,
  minAccountAgeHours: 0,
  eligibilityRules: { organizationIds: [], allowedRoles: [] },
  ruleVersion: 1,
  createdBy: "admin-1",
  createdAt: "2026-08-01T00:00:00Z",
  updatedAt: "2026-08-01T00:00:00Z",
};

const participant = {
  id: "participant-1",
  campaignId: campaign.id,
  workId: "work-1",
  status: "PENDING" as const,
  title: "Tác phẩm hiện tại",
  slug: "tac-pham-hien-tai",
  approvedAt: null,
  createdAt: "2026-08-02T00:00:00Z",
  updatedAt: "2026-08-02T00:00:00Z",
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.mocked(votingCampaignAdminApi.list).mockResolvedValue({
    success: true,
    data: [campaign],
    meta: { page: 1, pageSize: 100, total: 1 },
  });
  vi.mocked(votingCampaignAdminApi.participants).mockResolvedValue({
    success: true,
    data: [participant],
    meta: { page: 1, pageSize: 100, total: 1 },
  });
  vi.mocked(publicApi.search).mockResolvedValue({
    success: true,
    data: [
      {
        id: "work-2",
        slug: "tac-pham-moi",
        title: "Tác phẩm mới",
        shortDescription: "Mô tả",
        authorDisplayName: null,
        categoryName: "Sáng tạo",
        categorySlug: "sang-tao",
        certificateNumber: null,
        certificateStatus: null,
        publishedAt: "2026-08-01T00:00:00Z",
      },
    ],
    meta: { requestId: "search-1", nextCursor: null, durationMs: 2, version: "v1" },
  });
  vi.mocked(votingCampaignAdminApi.bulkAdd).mockResolvedValue([]);
  vi.mocked(votingCampaignAdminApi.transition).mockResolvedValue({
    ...participant,
    status: "APPROVED",
  });
});

describe("VotingParticipantWorkspace", () => {
  it("searches public works, bulk adds and approves with a required reason", async () => {
    const user = userEvent.setup();
    render(<VotingParticipantWorkspace />, { wrapper });

    expect(await screen.findByText("Tác phẩm hiện tại")).toBeTruthy();
    await user.type(screen.getByLabelText("Lý do thao tác"), "Đã kiểm tra");
    await user.type(screen.getByLabelText("Tìm tác phẩm công khai"), "Tác phẩm");
    await user.click(screen.getByRole("button", { name: "Tìm kiếm" }));
    await user.click(await screen.findByRole("checkbox", { name: "Chọn Tác phẩm mới" }));
    await user.click(screen.getByRole("button", { name: "Thêm 1 tác phẩm" }));
    await waitFor(() =>
      expect(votingCampaignAdminApi.bulkAdd).toHaveBeenCalledWith(
        campaign.id,
        ["work-2"],
        "Đã kiểm tra",
      ),
    );

    await user.click(screen.getByRole("button", { name: "Duyệt Tác phẩm hiện tại" }));
    expect(votingCampaignAdminApi.transition).toHaveBeenCalledWith(
      campaign.id,
      participant.id,
      "approve",
      "Đã kiểm tra",
    );
  });
});
