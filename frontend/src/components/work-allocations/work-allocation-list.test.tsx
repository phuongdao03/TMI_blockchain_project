import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkAllocationList } from "@/components/work-allocations/work-allocation-list";
import type { WorkAllocationDetail } from "@/lib/api/types";

const dossierAllocation = {
  id: "allocation-1",
  kind: "DOSSIER_REVIEW" as const,
  objective: "Thẩm định hồ sơ HS-2026-01",
  description: null,
  dossierId: "dossier-1",
  dossierVersionId: "version-1",
  dueAt: null,
  priority: "MEDIUM" as const,
  status: "ACTIVE" as const,
  createdByUserId: "admin-1",
  createdAt: "2026-09-22T08:00:00Z",
  updatedAt: "2026-09-22T08:00:00Z",
};

const allocationDetail: WorkAllocationDetail = {
  ...dossierAllocation,
  scopes: [
    {
      id: "scope-1",
      allocationId: "allocation-1",
      scopeType: "EVIDENCE",
      dossierEvidenceId: "evidence-1",
      dossierEvidenceTitle: "Bản thảo chính",
      groupLabel: null,
      requiresDualReview: true,
      createdAt: "2026-09-22T08:00:00Z",
      updatedAt: "2026-09-22T08:00:00Z",
    },
  ],
  members: [],
  scopeCoverage: [
    {
      scopeId: "scope-1",
      reviewAssignmentIds: ["assignment-1", "assignment-2"],
      reviewerUserIds: ["moderator-1", "moderator-2"],
    },
  ],
};

describe("WorkAllocationList", () => {
  it("shows real assignee progress for a general allocation", () => {
    render(
      <WorkAllocationList
        isDetailError={false}
        isDetailPending={false}
        isError={false}
        isPending={false}
        onSelect={vi.fn()}
        rows={[
          {
            ...dossierAllocation,
            kind: "GENERIC",
            dossierId: null,
            dossierVersionId: null,
          },
        ]}
        selectedAllocationId="allocation-1"
        selectedDetail={{
          ...allocationDetail,
          kind: "GENERIC",
          dossierId: null,
          dossierVersionId: null,
          scopes: [],
          scopeCoverage: [],
          members: [
            {
              id: "member-1",
              allocationId: "allocation-1",
              userId: "moderator-1",
              responsibility: "LEAD",
              assignedByUserId: "admin-1",
              isActive: true,
              deactivatedAt: null,
              completedAt: "2026-10-08T00:00:00Z",
              createdAt: "2026-10-01T00:00:00Z",
              updatedAt: "2026-10-08T00:00:00Z",
            },
          ],
        }}
        memberLabels={{ "moderator-1": "linh@example.com" }}
      />,
    );
    expect(screen.getByText("Người thực hiện · 1/1 hoàn thành")).toBeDefined();
    expect(
      screen.getByText("linh@example.com · Phụ trách chính"),
    ).toBeDefined();
    expect(screen.getByText("Đã xong")).toBeDefined();
  });
  it("lets an admin activate an existing general draft", () => {
    const activateDraft = vi.fn();
    render(
      <WorkAllocationList
        isDetailError={false}
        isDetailPending={false}
        isError={false}
        isPending={false}
        onActivateDraft={activateDraft}
        onSelect={vi.fn()}
        rows={[
          {
            ...dossierAllocation,
            id: "draft-1",
            kind: "GENERIC",
            dossierId: null,
            dossierVersionId: null,
            status: "DRAFT",
          },
        ]}
        selectedAllocationId={null}
        selectedDetail={null}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Kích hoạt và giao việc" }),
    );
    expect(activateDraft).toHaveBeenCalledWith("draft-1");
  });

  it("reveals named document coverage for a selected dossier allocation", () => {
    const selectAllocation = vi.fn();

    const { rerender } = render(
      <WorkAllocationList
        isDetailError={false}
        isDetailPending={false}
        isError={false}
        isPending={false}
        onSelect={selectAllocation}
        rows={[dossierAllocation]}
        selectedAllocationId={null}
        selectedDetail={null}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Xem phạm vi" }));
    expect(selectAllocation).toHaveBeenCalledWith("allocation-1");

    rerender(
      <WorkAllocationList
        isDetailError={false}
        isDetailPending={false}
        isError={false}
        isPending={false}
        onSelect={selectAllocation}
        rows={[dossierAllocation]}
        selectedAllocationId="allocation-1"
        selectedDetail={allocationDetail}
      />,
    );

    expect(screen.getByText("Bản thảo chính")).toBeDefined();
    expect(screen.getByText("Thẩm định kép · 2 người phụ trách")).toBeDefined();
  });
});
