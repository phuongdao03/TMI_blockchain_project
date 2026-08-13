import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SimilarityReviewWorkspace } from "@/components/reviews/similarity-review-workspace";

const listReviewer = vi.hoisted(() => vi.fn());
const resolve = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  similarityApi: { listReviewer, resolve },
  mediaApi: { signedUrl: vi.fn() },
}));

const item = {
  id: "case-1",
  leftDossierVersionId: "version-1",
  rightDossierVersionId: "version-2",
  leftAsset: {
    dossierId: "dossier-1",
    dossierCode: "HS-001",
    dossierTitle: "Bình minh trên sông",
    versionNo: 1,
    evidenceMediaIds: ["media-1"],
  },
  rightAsset: {
    dossierId: "dossier-2",
    dossierCode: "HS-002",
    dossierTitle: "Bình minh bên sông",
    versionNo: 1,
    evidenceMediaIds: ["media-2"],
  },
  signalType: "TEXT",
  textScore: 0.91,
  imageDistance: null,
  policyVersion: "near-duplicate-v1",
  status: "ASSIGNED",
  assignedReviewerUserId: "reviewer-1",
  disposition: null,
  resolutionReason: null,
  createdAt: "2026-08-10T10:00:00Z",
  assignedAt: "2026-08-10T11:00:00Z",
  resolvedAt: null,
} as const;

describe("SimilarityReviewWorkspace", () => {
  it("guides a reviewer with user language and records a reasoned decision", async () => {
    listReviewer.mockResolvedValue({
      success: true,
      data: [item],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 1 },
    });
    resolve.mockResolvedValue({ ...item, status: "RESOLVED" });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const user = userEvent.setup();

    render(
      <QueryClientProvider client={client}>
        <SimilarityReviewWorkspace />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Bình minh trên sông")).toBeDefined();
    expect(screen.getByText("Bình minh bên sông")).toBeDefined();
    expect(screen.getByText("Nội dung có dấu hiệu tương đồng")).toBeDefined();
    expect(screen.queryByText("TEXT")).toBeNull();
    expect(screen.queryByText("near-duplicate-v1")).toBeNull();

    await user.selectOptions(
      screen.getByLabelText("Kết luận đối chiếu"),
      "RELATED",
    );
    await user.type(
      screen.getByLabelText("Căn cứ cho kết luận"),
      "Hai tác phẩm thuộc cùng một bộ sưu tập nhưng là hai bản độc lập.",
    );
    await user.click(
      screen.getByRole("button", { name: "Hoàn tất đối chiếu" }),
    );

    expect(resolve).toHaveBeenCalledWith("case-1", {
      disposition: "RELATED",
      reason:
        "Hai tác phẩm thuộc cùng một bộ sưu tập nhưng là hai bản độc lập.",
    });
  });
});
