import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReviewAssignmentQueue } from "@/components/admin/review-assignment-queue";

const list = vi.hoisted(() => vi.fn());
const get = vi.hoisted(() => vi.fn());
const assign = vi.hoisted(() => vi.fn());
const listStaff = vi.hoisted(() => vi.fn());
const push = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

vi.mock("@/lib/api/client", () => ({
  adminReviewApi: {
    list,
    get,
    assign,
    startPrecheck: vi.fn(),
    passPrecheck: vi.fn(),
    requestSupplement: vi.fn(),
  },
  staffAccountsApi: { list: listStaff },
}));
vi.mock("@/components/reviews/evidence-viewer", () => ({
  EvidenceViewer: () => <div>Tài liệu hồ sơ</div>,
}));

function renderQueue(initialDossierId?: string) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <ReviewAssignmentQueue initialDossierId={initialDossierId} />
    </QueryClientProvider>,
  );
}

describe("ReviewAssignmentQueue", () => {
  it("shows submitted dossiers in the admin handoff queue", async () => {
    list.mockResolvedValue({
      data: [
        {
          dossierId: "dossier-1",
          dossierCode: "TMI-001",
          dossierTitle: "Hồ sơ cần duyệt",
          status: "SUBMITTED",
          versionNo: 1,
          submittedAt: "2026-09-07T00:00:00Z",
          assignmentCount: 0,
        },
      ],
      meta: { total: 1 },
    });

    renderQueue();

    expect(await screen.findByText("Hồ sơ cần duyệt")).toBeDefined();
    expect(
      screen.getByRole("link", { name: /Xem và xử lý/ }).getAttribute("href"),
    ).toBe("/admin/reviews/dossier-1");
  });

  it("lets an admin assign an active reviewer", async () => {
    get.mockResolvedValue({
      dossierId: "dossier-1",
      dossierCode: "TMI-001",
      dossierTitle: "Hồ sơ cần duyệt",
      status: "UNDER_REVIEW",
      versionNo: 1,
      submittedAt: "2026-09-07T00:00:00Z",
      assignmentCount: 0,
      canonicalHash: "hash",
      snapshotJson: {
        schemaVersion: 1,
        dossier: { id: "dossier-1", code: "TMI-001", title: "Hồ sơ cần duyệt" },
        evidences: [],
      },
    });
    listStaff.mockResolvedValue({
      data: [
        {
          id: "reviewer-1",
          email: "reviewer@tmi.vn",
          role: "MODERATOR",
          status: "ACTIVE",
        },
      ],
      meta: { total: 1 },
    });
    assign.mockResolvedValue([]);
    const user = userEvent.setup();

    renderQueue("dossier-1");

    await screen.findByRole("option", { name: "reviewer@tmi.vn" });
    await user.selectOptions(
      await screen.findByLabelText("Nhân viên thẩm định"),
      "reviewer-1",
    );
    await user.click(
      screen.getByRole("button", { name: "Phân công thẩm định" }),
    );
    expect(assign).toHaveBeenCalledWith("dossier-1", ["reviewer-1"], undefined);
  });
});
