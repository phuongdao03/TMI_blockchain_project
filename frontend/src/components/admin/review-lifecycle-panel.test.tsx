import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReviewLifecyclePanel } from "@/components/admin/review-lifecycle-panel";
import type { AdminReviewDossierDetail } from "@/lib/api/types";

const approveAssistanceRequestMock = vi.hoisted(() => vi.fn());
const listStaffMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api/client", () => ({
  adminReviewApi: {
    approveAssistanceRequest: approveAssistanceRequestMock,
    assign: vi.fn(),
    decide: vi.fn(),
    declineAssistanceRequest: vi.fn(),
    passPrecheck: vi.fn(),
    requestSupplement: vi.fn(),
    startPrecheck: vi.fn(),
  },
  staffAccountsApi: { list: listStaffMock },
}));

const dossier: AdminReviewDossierDetail = {
  dossierId: "dossier-1",
  dossierCode: "HS-2026-01",
  dossierTitle: "Hồ sơ cần phối hợp",
  status: "UNDER_REVIEW",
  versionNo: 1,
  submittedAt: "2026-09-21T08:00:00.000Z",
  assignmentCount: 0,
  canonicalHash: "a".repeat(64),
  snapshotJson: {
    schemaVersion: 1,
    dossier: { id: "dossier-1", code: "HS-2026-01", title: "Hồ sơ" },
    evidences: [],
  },
  assignments: [],
  assistanceRequests: [
    {
      requesterEmail: "moderator@cns.vn",
      request: {
        id: "request-1",
        assignmentId: "assignment-1",
        requestedByUserId: "moderator-1",
        requestedReviewerCount: 1,
        reason: "Cần một chuyên gia khác đối chiếu bộ chứng cứ chuyên ngành.",
        status: "PENDING",
        createdAt: "2026-09-21T08:00:00.000Z",
        reviewedByUserId: null,
        decisionReason: null,
        reviewedAt: null,
      },
    },
  ],
};

describe("ReviewLifecyclePanel", () => {
  it("requires the exact requested reviewer selection before approval", async () => {
    const user = userEvent.setup();
    listStaffMock.mockResolvedValue({
      data: [{ id: "moderator-2", email: "specialist@cns.vn" }],
      meta: { page: 1, pageSize: 100, total: 1 },
    });
    approveAssistanceRequestMock.mockResolvedValue({ id: "request-1" });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <ReviewLifecyclePanel dossier={dossier} />
      </QueryClientProvider>,
    );

    const approve = await screen.findByRole("button", {
      name: "Thêm 1 moderator",
    });
    expect((approve as HTMLButtonElement).disabled).toBe(true);

    await user.click(await screen.findByLabelText("specialist@cns.vn"));
    await user.click(approve);

    expect(approveAssistanceRequestMock).toHaveBeenCalledWith(
      "request-1",
      ["moderator-2"],
      undefined,
    );
  });
});
