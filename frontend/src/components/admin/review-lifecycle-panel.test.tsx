import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReviewLifecyclePanel } from "@/components/admin/review-lifecycle-panel";
import type { AdminReviewDossierDetail } from "@/lib/api/types";

const approveAssistanceRequestMock = vi.hoisted(() => vi.fn());
const listStaffMock = vi.hoisted(() => vi.fn());
const assignMock = vi.hoisted(() => vi.fn());
const decideMock = vi.hoisted(() => vi.fn());
const supplementMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api/client", () => ({
  adminReviewApi: {
    approveAssistanceRequest: approveAssistanceRequestMock,
    assign: assignMock,
    decide: decideMock,
    declineAssistanceRequest: vi.fn(),
    passPrecheck: vi.fn(),
    requestSupplement: supplementMock,
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

function readyDossier(): AdminReviewDossierDetail {
  return {
    ...dossier,
    assignmentCount: 1,
    assistanceRequests: [],
    assignments: [
      {
        reviewerEmail: "moderator@cns.vn",
        assignment: {
          id: "assignment-1",
          reviewerUserId: "moderator-1",
          status: "SUBMITTED",
        },
        review: {
          submittedAt: "2026-09-22T08:00:00.000Z",
          recommendation: "APPROVE",
          totalScore: 85,
          applicantFeedback: null,
          privateNote: null,
        },
      },
    ],
  } as unknown as AdminReviewDossierDetail;
}

describe("ReviewLifecyclePanel", () => {
  beforeEach(() => vi.resetAllMocks());

  it("explains the admin handoff and the next place to track review", async () => {
    const user = userEvent.setup();
    listStaffMock.mockResolvedValue({
      data: [{ id: "moderator-2", email: "specialist@cns.vn" }],
      meta: { page: 1, pageSize: 100, total: 1 },
    });
    assignMock.mockResolvedValue([{ id: "assignment-2" }]);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <ReviewLifecyclePanel
          dossier={{ ...dossier, assistanceRequests: [] }}
        />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Bước 1 · Giao người kiểm duyệt")).toBeTruthy();
    await screen.findByRole("option", { name: "specialist@cns.vn" });
    await user.selectOptions(
      screen.getByLabelText("Người kiểm duyệt"),
      "moderator-2",
    );
    await user.click(
      screen.getByRole("button", { name: "Phân công kiểm duyệt" }),
    );

    expect(
      await screen.findByText("Đã giao hồ sơ cho người kiểm duyệt"),
    ).toBeTruthy();
    expect(screen.getByText(/sẽ nhận phân công trong hàng đợi/)).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: "Theo dõi thẩm định" })
        .getAttribute("href"),
    ).toBe("/admin/reviews");
  });

  it("keeps the approval result visible with a deliberate next action", async () => {
    const user = userEvent.setup();
    listStaffMock.mockResolvedValue({ data: [], meta: { total: 0 } });
    decideMock.mockResolvedValue({ status: "APPROVED" });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ReviewLifecyclePanel dossier={readyDossier()} />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Bước 3 · Ra quyết định cuối")).toBeTruthy();
    await user.type(
      screen.getByLabelText("Lý do quyết định cuối"),
      "Báo cáo đủ căn cứ.",
    );
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Phê duyệt hồ sơ" }));

    expect(await screen.findByText("Đã phê duyệt hồ sơ")).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: "Quyết định phí hồ sơ" })
        .getAttribute("href"),
    ).toBe("/admin/payments?dossierId=dossier-1");
  });

  it("explains what follows a supplement request", async () => {
    const user = userEvent.setup();
    listStaffMock.mockResolvedValue({ data: [], meta: { total: 0 } });
    supplementMock.mockResolvedValue({ status: "NEEDS_SUPPLEMENT" });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ReviewLifecyclePanel dossier={readyDossier()} />
      </QueryClientProvider>,
    );

    await user.type(
      screen.getByLabelText("Lý do quyết định cuối"),
      "Vui lòng bổ sung tài liệu nguồn gốc.",
    );
    await user.click(screen.getByRole("button", { name: "Yêu cầu bổ sung" }));

    expect(await screen.findByText("Đã gửi yêu cầu bổ sung")).toBeTruthy();
    expect(screen.getByText(/Người gửi cần bổ sung hồ sơ/)).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: "Về hàng chờ hồ sơ" })
        .getAttribute("href"),
    ).toBe("/admin/reviews");
  });

  it("asks for reassignment when every reviewer ended without a report", () => {
    listStaffMock.mockResolvedValue({ data: [], meta: { total: 0 } });
    const ended = readyDossier();
    const assignment = ended.assignments[0];
    if (!assignment) throw new Error("Expected a reviewer assignment");
    assignment.assignment.status = "CONFLICTED";
    assignment.review = null;
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ReviewLifecyclePanel dossier={ended} />
      </QueryClientProvider>,
    );

    expect(
      screen.getByText("Bước 1 · Phân công lại người kiểm duyệt"),
    ).toBeTruthy();
    expect(screen.getByText(/Chưa có báo cáo hợp lệ/)).toBeTruthy();
  });

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
    expect(await screen.findByText("Đã bổ sung người kiểm duyệt")).toBeTruthy();
  });
});
