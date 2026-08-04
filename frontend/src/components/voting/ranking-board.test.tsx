import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RankingBoard } from "@/components/voting/ranking-board";
import { rankingApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({ rankingApi: { public: vi.fn() } }));

const ranking = {
  snapshot: {
    id: "snapshot-1", campaignId: "campaign-1", version: 2,
    formulaVersion: "effective-votes-v1", campaignRuleVersion: 1,
    sourceDigest: "a".repeat(64), resultDigest: "b".repeat(64),
    candidateCount: 2, totalValidVotes: 13, createdAt: "2026-08-03T08:00:00Z",
  },
  items: [
    {
      workId: "work-1", slug: "heritage-work", title: "Heritage work",
      shortDescription: "A public ranked work.", authorDisplayName: "Nguyễn An",
      categoryId: "category-1", categoryName: "Di sản", categorySlug: "di-san",
      rank: 1, categoryRank: 1, displayOrder: 1, score: 8, effectiveVoteCount: 8,
    },
    {
      workId: "work-2", slug: "craft-work", title: "Craft work",
      shortDescription: "Another public ranked work.", authorDisplayName: null,
      categoryId: "category-1", categoryName: "Di sản", categorySlug: "di-san",
      rank: 2, categoryRank: 2, displayOrder: 2, score: 5, effectiveVoteCount: 5,
    },
  ],
  pagination: { page: 1, pageSize: 20, total: 2 },
};

function renderBoard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><RankingBoard slug="heritage-campaign" /></QueryClientProvider>);
}

describe("RankingBoard", () => {
  it("renders immutable snapshot metadata and ranked public works", async () => {
    vi.mocked(rankingApi.public).mockResolvedValue(ranking);
    renderBoard();
    expect(await screen.findByRole("heading", { name: "Bảng xếp hạng" })).toBeTruthy();
    expect(screen.getByText("Heritage work")).toBeTruthy();
    expect(screen.getByText("Snapshot bbbbbbbbbbbb…")).toBeTruthy();
  });

  it("shows a safe preparation state when the public snapshot is unavailable", async () => {
    vi.mocked(rankingApi.public).mockRejectedValue(new Error("not found"));
    renderBoard();
    expect(await screen.findByRole("heading", { name: "Kết quả đang được chuẩn bị" })).toBeTruthy();
  });
});
