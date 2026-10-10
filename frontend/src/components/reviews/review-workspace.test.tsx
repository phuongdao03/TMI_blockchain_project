import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReviewWorkspace } from "@/components/reviews/review-workspace";

const getReview = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  reviewApi: {
    get: getReview,
    saveDraft: vi.fn(),
    declareConflict: vi.fn(),
    submit: vi.fn(),
  },
}));
vi.mock("@/components/reviews/evidence-viewer", () => ({
  EvidenceViewer: () => <div>Danh sách tài liệu</div>,
}));
vi.mock("@/components/reviews/five-t-scorecard", () => ({
  FiveTScorecard: () => <div>Phiếu thẩm định</div>,
}));
vi.mock("@/components/reviews/review-assistance-panel", () => ({
  ReviewAssistancePanel: () => null,
}));

describe("ReviewWorkspace", () => {
  beforeEach(() => {
    getReview.mockReset().mockResolvedValue({
      assignment: { status: "IN_PROGRESS", dueAt: null },
      dossierCode: "THV-001",
      dossierTitle: "Tác phẩm văn hóa",
      versionNo: 1,
      canonicalHash: "abc123",
      review: null,
      snapshotJson: {
        schemaVersion: 1,
        dossier: { summary: "Câu chuyện tác phẩm", dossierType: null },
        evidences: [],
      },
    });
  });

  it("lets reviewers jump directly to evidence and the assessment form", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ReviewWorkspace assignmentId="assignment-1" />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Tác phẩm văn hóa")).toBeDefined();
    expect(
      screen.getByRole("link", { name: "Xem tài liệu" }).getAttribute("href"),
    ).toBe("#review-evidence");
    expect(
      screen
        .getByRole("link", { name: "Mở phiếu thẩm định" })
        .getAttribute("href"),
    ).toBe("#review-scorecard");
    expect(document.getElementById("review-evidence")).toBeDefined();
    expect(document.getElementById("review-scorecard")).toBeDefined();
  });
});
