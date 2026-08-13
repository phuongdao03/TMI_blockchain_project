import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CampaignDetail } from "@/components/voting/campaign-detail";
import { authApi, votingApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  authApi: { currentUser: vi.fn() },
  votingApi: {
    campaign: vi.fn(),
    works: vi.fn(),
    summary: vi.fn(),
    eligibility: vi.fn(),
    myVotes: vi.fn(),
    createVote: vi.fn(),
    changeVote: vi.fn(),
    revokeVote: vi.fn(),
  },
  rankingApi: { public: vi.fn() },
}));

const campaign = {
  id: "campaign-1",
  name: "Bình chọn tháng 8",
  slug: "thang-8",
  description: "Chọn tác phẩm tạo ảnh hưởng tích cực.",
  status: "ACTIVE" as const,
  timezone: "Asia/Ho_Chi_Minh",
  startAt: "2026-08-03T07:00:00Z",
  endAt: "2026-08-04T08:00:00Z",
  maxVotesPerUser: 1,
  allowVoteChange: true,
  allowVoteRevoke: true,
  ruleVersion: 1,
  serverTime: "2026-08-03T08:00:00Z",
};

function setupData() {
  vi.mocked(votingApi.campaign).mockResolvedValue(campaign);
  vi.mocked(votingApi.works).mockResolvedValue([
    {
      workId: "work-1",
      title: "Di sản số",
      slug: "di-san-so",
      shortDescription: "Tác phẩm công khai",
    },
  ]);
  vi.mocked(votingApi.summary).mockResolvedValue([
    {
      workId: "work-1",
      workTitle: "Di sản số",
      workSlug: "di-san-so",
      effectiveCount: 7,
      refreshedAt: "2026-08-03T08:00:00Z",
    },
  ]);
}

function renderDetail() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <CampaignDetail slug="thang-8" />
    </QueryClientProvider>,
  );
}

describe("CampaignDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupData();
  });

  it("shows a return-safe login CTA to guests", async () => {
    vi.mocked(authApi.currentUser).mockRejectedValue(new Error("unauthorized"));
    renderDetail();
    const login = await screen.findByRole("link", {
      name: "Đăng nhập để chọn",
    });
    expect(login.getAttribute("href")).toBe("/login?next=/voting/thang-8");
    expect(screen.getByText("7 phiếu")).toBeTruthy();
  });

  it("locks the vote CTA while the request is pending", async () => {
    vi.mocked(authApi.currentUser).mockResolvedValue({
      id: "user-1",
      email: "voter@example.test",
      roles: ["PUBLIC_USER"],
      accountType: null,
    });
    vi.mocked(votingApi.eligibility).mockResolvedValue({
      canVote: true,
      reasons: [],
      remainingQuota: 1,
      ruleVersion: 1,
      serverTime: campaign.serverTime,
    });
    vi.mocked(votingApi.myVotes).mockResolvedValue({
      success: true,
      data: [],
      meta: { page: 1, pageSize: 20, total: 0 },
    });
    vi.mocked(votingApi.createVote).mockImplementation(
      () => new Promise(() => undefined),
    );
    renderDetail();
    const button = await screen.findByRole("button", { name: "Bình chọn" });
    await userEvent.click(button);
    expect(button).toHaveProperty("disabled", true);
    await userEvent.click(button);
    expect(votingApi.createVote).toHaveBeenCalledTimes(1);
  });
});
