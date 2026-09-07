import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReviewAssignmentQueue } from "@/components/admin/review-assignment-queue";

const list = vi.hoisted(() => vi.fn());
const get = vi.hoisted(() => vi.fn());
const assign = vi.hoisted(() => vi.fn());
const passPrecheck = vi.hoisted(() => vi.fn());
const decide = vi.hoisted(() => vi.fn());
const listStaff = vi.hoisted(() => vi.fn());
const push = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

vi.mock("@/lib/api/client", () => ({
  adminReviewApi: {
    list,
    get,
    assign,
    startPrecheck: vi.fn(),
    passPrecheck,
    requestSupplement: vi.fn(),
    decide,
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
      assignments: [],
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
      await screen.findByLabelText("Người kiểm duyệt"),
      "reviewer-1",
    );
    await user.click(
      screen.getByRole("button", { name: "Phân công người kiểm duyệt" }),
    );
    expect(assign).toHaveBeenCalledWith("dossier-1", ["reviewer-1"], undefined);
  });

  it("prechecks and assigns the selected reviewer in one guided action", async () => {
    get.mockResolvedValue({
      dossierId: "dossier-1",
      dossierCode: "TMI-001",
      dossierTitle: "Hồ sơ cần duyệt",
      status: "PRECHECK",
      versionNo: 1,
      submittedAt: "2026-09-07T00:00:00Z",
      assignmentCount: 0,
      canonicalHash: "hash",
      snapshotJson: {
        schemaVersion: 1,
        dossier: { id: "dossier-1", code: "TMI-001", title: "Hồ sơ cần duyệt" },
        evidences: [],
      },
      assignments: [],
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
    passPrecheck.mockResolvedValue({
      dossierId: "dossier-1",
      status: "UNDER_REVIEW",
    });
    assign.mockResolvedValue([]);
    const user = userEvent.setup();

    renderQueue("dossier-1");

    await user.type(
      await screen.findByLabelText("Ghi chú sơ kiểm"),
      "Tài liệu hợp lệ",
    );
    await user.selectOptions(
      screen.getByLabelText("Người kiểm duyệt"),
      "reviewer-1",
    );
    await user.click(
      screen.getByRole("button", { name: "Đạt sơ kiểm và phân công" }),
    );

    expect(passPrecheck).toHaveBeenCalledWith("dossier-1", "Tài liệu hợp lệ");
    expect(assign).toHaveBeenCalledWith("dossier-1", ["reviewer-1"], undefined);
  });

  it("shows the submitted reviewer report to the admin", async () => {
    get.mockResolvedValue({
      dossierId: "dossier-1",
      dossierCode: "TMI-001",
      dossierTitle: "Hồ sơ cần duyệt",
      status: "UNDER_REVIEW",
      versionNo: 1,
      submittedAt: "2026-09-07T00:00:00Z",
      assignmentCount: 1,
      canonicalHash: "hash",
      snapshotJson: {
        schemaVersion: 1,
        dossier: { id: "dossier-1", code: "TMI-001", title: "Hồ sơ cần duyệt" },
        evidences: [],
      },
      assignments: [
        {
          reviewerEmail: "reviewer@tmi.vn",
          assignment: { id: "assignment-1", status: "SUBMITTED" },
          review: {
            recommendation: "APPROVE",
            totalScore: 90,
            submittedAt: "2026-09-07T01:00:00Z",
            applicantFeedback: "Hồ sơ đạt yêu cầu.",
            privateNote: "Đã đối chiếu bản gốc.",
            findings: [],
          },
        },
      ],
    });
    listStaff.mockResolvedValue({ data: [], meta: { total: 0 } });

    renderQueue("dossier-1");

    expect(await screen.findByText("Báo cáo kiểm duyệt")).toBeDefined();
    expect(screen.getByText("reviewer@tmi.vn")).toBeDefined();
    expect(screen.getByText("Đề nghị phê duyệt")).toBeDefined();
    expect(screen.getByText("Hồ sơ đạt yêu cầu.")).toBeDefined();
  });

  it("allows final admin approval only after reviewer reports are complete", async () => {
    get.mockResolvedValue({
      dossierId: "dossier-1",
      dossierCode: "TMI-001",
      dossierTitle: "Hồ sơ cần duyệt",
      status: "UNDER_REVIEW",
      versionNo: 1,
      submittedAt: "2026-09-07T00:00:00Z",
      assignmentCount: 1,
      canonicalHash: "hash",
      snapshotJson: {
        schemaVersion: 1,
        dossier: { id: "dossier-1", code: "TMI-001", title: "Hồ sơ cần duyệt" },
        evidences: [],
      },
      assignments: [
        {
          reviewerEmail: "reviewer@tmi.vn",
          assignment: { id: "assignment-1", status: "SUBMITTED" },
          review: {
            recommendation: "APPROVE",
            totalScore: 90,
            submittedAt: "2026-09-07T01:00:00Z",
            applicantFeedback: "Hồ sơ đạt yêu cầu.",
            privateNote: null,
            findings: [],
          },
        },
      ],
    });
    listStaff.mockResolvedValue({ data: [], meta: { total: 0 } });
    decide.mockResolvedValue({ dossierId: "dossier-1", status: "APPROVED" });
    const user = userEvent.setup();

    renderQueue("dossier-1");

    await user.type(
      await screen.findByLabelText("Lý do quyết định cuối"),
      "Đồng ý với báo cáo kiểm duyệt",
    );
    await user.click(screen.getByLabelText(/không có xung đột lợi ích/i));
    await user.click(screen.getByRole("button", { name: "Phê duyệt hồ sơ" }));

    expect(decide).toHaveBeenCalledWith(
      "dossier-1",
      "APPROVE",
      "Đồng ý với báo cáo kiểm duyệt",
      true,
    );
    expect(push).toHaveBeenCalledWith("/blockchain");
  });
});
