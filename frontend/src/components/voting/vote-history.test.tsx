import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { VoteHistory } from "@/components/voting/vote-history";
import { votingApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({ votingApi: { myVotes: vi.fn() } }));

function renderHistory() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <VoteHistory />
    </QueryClientProvider>,
  );
}

describe("VoteHistory", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders only server-approved actions", async () => {
    vi.mocked(votingApi.myVotes).mockResolvedValue({
      success: true,
      data: [
        {
          voteId: "vote-1",
          campaignId: "campaign-1",
          campaignName: "Bình chọn tháng 8",
          campaignSlug: "binh-chon-thang-8",
          workId: "work-1",
          workTitle: "Di sản số Việt",
          workSlug: "di-san-so-viet",
          status: "VALID",
          createdAt: "2026-08-03T08:00:00Z",
          revokedAt: null,
          canChange: true,
          canRevoke: false,
        },
      ],
      meta: { page: 1, pageSize: 20, total: 1 },
    });
    renderHistory();
    expect(await screen.findByText("Di sản số Việt")).toBeTruthy();
    expect(screen.getByText("Có thể đổi lựa chọn")).toBeTruthy();
    expect(screen.queryByText("Có thể thu hồi")).toBeNull();
  });

  it("shows an explicit empty state", async () => {
    vi.mocked(votingApi.myVotes).mockResolvedValue({
      success: true,
      data: [],
      meta: { page: 1, pageSize: 20, total: 0 },
    });
    renderHistory();
    expect(await screen.findByText("Bạn chưa bình chọn")).toBeTruthy();
  });
});
