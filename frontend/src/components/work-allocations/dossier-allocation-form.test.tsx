import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DossierAllocationForm } from "@/components/work-allocations/dossier-allocation-form";

const allocationCreateMock = vi.hoisted(() => vi.fn());
const allocationGetMock = vi.hoisted(() => vi.fn());
const allocationActivateMock = vi.hoisted(() => vi.fn());
const dossierListMock = vi.hoisted(() => vi.fn());
const dossierGetMock = vi.hoisted(() => vi.fn());
const assignMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  adminReviewApi: {
    list: dossierListMock,
    get: dossierGetMock,
    assign: assignMock,
  },
  workAllocationAdminApi: {
    create: allocationCreateMock,
    get: allocationGetMock,
    activate: allocationActivateMock,
  },
}));

describe("DossierAllocationForm", () => {
  it("creates and activates document coverage with an existing reviewer assignment", async () => {
    dossierListMock.mockResolvedValue({
      success: true,
      data: [
        {
          dossierId: "dossier-1",
          dossierCode: "HS-2026-01",
          dossierTitle: "Tác phẩm Mùa nước nổi",
          status: "UNDER_REVIEW",
          versionNo: 3,
          submittedAt: "2026-09-20T08:00:00Z",
          assignmentCount: 1,
        },
      ],
      meta: { page: 1, pageSize: 50, total: 1 },
    });
    dossierGetMock.mockResolvedValue({
      dossierId: "dossier-1",
      dossierCode: "HS-2026-01",
      dossierTitle: "Tác phẩm Mùa nước nổi",
      status: "UNDER_REVIEW",
      versionNo: 3,
      submittedAt: "2026-09-20T08:00:00Z",
      assignmentCount: 1,
      canonicalHash: "hash",
      snapshotJson: {
        schemaVersion: 1,
        dossier: {
          id: "dossier-1",
          code: "HS-2026-01",
          title: "Tác phẩm Mùa nước nổi",
        },
        evidences: [
          {
            id: "evidence-1",
            mediaAssetId: "media-1",
            evidenceType: "DOCUMENT",
            title: "Bản thảo chính",
            description: null,
            issuedAt: null,
            displayOrder: 1,
            isPublic: false,
            media: { mimeType: "application/pdf", bytes: 1024, sha256: "hash" },
          },
        ],
      },
      assignments: [
        {
          assignment: {
            id: "review-assignment-1",
            dossierId: "dossier-1",
            dossierVersionId: "version-1",
            reviewerUserId: "moderator-1",
            assignedBy: "admin-1",
            dueAt: null,
            status: "IN_PROGRESS",
            conflictDeclaredAt: null,
            conflictReason: null,
          },
          reviewerEmail: "linh.tran@example.com",
          review: null,
        },
      ],
    });
    allocationCreateMock.mockResolvedValue({ id: "allocation-1" });
    allocationGetMock.mockResolvedValue({
      scopes: [{ id: "scope-1", dossierEvidenceId: "evidence-1" }],
    });
    allocationActivateMock.mockResolvedValue({
      id: "allocation-1",
      status: "ACTIVE",
    });
    const onSaved = vi.fn().mockResolvedValue(undefined);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const user = userEvent.setup();

    render(
      <QueryClientProvider client={client}>
        <DossierAllocationForm
          onSaved={onSaved}
          staff={[
            {
              id: "moderator-1",
              email: "linh.tran@example.com",
              role: "MODERATOR",
              status: "ACTIVE",
              createdAt: null,
              lastLoginAt: null,
            },
          ]}
        />
      </QueryClientProvider>,
    );

    await screen.findByRole("option", { name: /HS-2026-01/ });
    await user.selectOptions(
      screen.getByLabelText("Hồ sơ cần thẩm định"),
      "dossier-1",
    );
    await waitFor(() => {
      expect(dossierGetMock).toHaveBeenCalledWith("dossier-1");
    });
    await screen.findByText("Tài liệu và phạm vi thẩm định");
    const evidence = await screen.findByRole("checkbox", {
      name: /Bản thảo chính/,
    });
    fireEvent.click(await screen.findByLabelText("linh.tran@example.com"));
    fireEvent.click(evidence);
    fireEvent.click(
      await screen.findByLabelText(
        "Phân công linh.tran@example.com · Bản thảo chính",
      ),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Tạo và kích hoạt phân công" }),
    );

    await waitFor(() => {
      expect(allocationCreateMock).toHaveBeenCalledWith({
        kind: "DOSSIER_REVIEW",
        objective: "Thẩm định hồ sơ HS-2026-01",
        description: null,
        dossierId: "dossier-1",
        dossierVersionId: "version-1",
        dueAt: null,
        priority: "MEDIUM",
        scopes: [
          {
            scopeType: "EVIDENCE",
            dossierEvidenceId: "evidence-1",
            requiresDualReview: false,
          },
        ],
        members: [{ userId: "moderator-1", responsibility: "REVIEWER" }],
      });
      expect(allocationActivateMock).toHaveBeenCalledWith("allocation-1", [
        {
          scopeId: "scope-1",
          reviewAssignmentIds: ["review-assignment-1"],
        },
      ]);
    });
    expect(assignMock).not.toHaveBeenCalled();
    expect(onSaved).toHaveBeenCalledOnce();
  });

  it("assigns a newly added moderator before activating document coverage", async () => {
    dossierListMock.mockResolvedValue({
      success: true,
      data: [
        {
          dossierId: "dossier-2",
          dossierCode: "HS-2026-02",
          dossierTitle: "Tác phẩm Mưa đầu mùa",
          status: "UNDER_REVIEW",
          versionNo: 1,
          submittedAt: "2026-09-20T08:00:00Z",
          assignmentCount: 0,
        },
      ],
      meta: { page: 1, pageSize: 50, total: 1 },
    });
    dossierGetMock.mockResolvedValue({
      dossierId: "dossier-2",
      dossierCode: "HS-2026-02",
      dossierTitle: "Tác phẩm Mưa đầu mùa",
      status: "UNDER_REVIEW",
      versionNo: 1,
      submittedAt: "2026-09-20T08:00:00Z",
      assignmentCount: 0,
      canonicalHash: "hash",
      snapshotJson: {
        schemaVersion: 1,
        dossier: {
          id: "dossier-2",
          code: "HS-2026-02",
          title: "Tác phẩm Mưa đầu mùa",
        },
        evidences: [
          {
            id: "evidence-2",
            mediaAssetId: "media-2",
            evidenceType: "DOCUMENT",
            title: "Hồ sơ minh chứng",
            description: null,
            issuedAt: null,
            displayOrder: 1,
            isPublic: false,
            media: { mimeType: "application/pdf", bytes: 1024, sha256: "hash" },
          },
        ],
      },
      assignments: [],
    });
    assignMock.mockResolvedValue([
      {
        id: "review-assignment-2",
        dossierId: "dossier-2",
        dossierVersionId: "version-2",
        reviewerUserId: "moderator-2",
        assignedBy: "admin-1",
        dueAt: null,
        status: "IN_PROGRESS",
        conflictDeclaredAt: null,
        conflictReason: null,
      },
    ]);
    allocationCreateMock.mockResolvedValue({ id: "allocation-2" });
    allocationGetMock.mockResolvedValue({
      scopes: [{ id: "scope-2", dossierEvidenceId: "evidence-2" }],
    });
    allocationActivateMock.mockResolvedValue({
      id: "allocation-2",
      status: "ACTIVE",
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <DossierAllocationForm
          onSaved={vi.fn().mockResolvedValue(undefined)}
          staff={[
            {
              id: "moderator-2",
              email: "minh.pham@example.com",
              role: "MODERATOR",
              status: "ACTIVE",
              createdAt: null,
              lastLoginAt: null,
            },
          ]}
        />
      </QueryClientProvider>,
    );

    await screen.findByRole("option", { name: /HS-2026-02/ });
    await userEvent
      .setup()
      .selectOptions(screen.getByLabelText("Hồ sơ cần thẩm định"), "dossier-2");
    await screen.findByText("Tài liệu và phạm vi thẩm định");
    fireEvent.click(screen.getByLabelText("minh.pham@example.com"));
    fireEvent.click(screen.getByRole("checkbox", { name: /Hồ sơ minh chứng/ }));
    fireEvent.click(
      screen.getByLabelText(
        "Phân công minh.pham@example.com · Hồ sơ minh chứng",
      ),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Tạo và kích hoạt phân công" }),
    );

    await waitFor(() => {
      expect(assignMock).toHaveBeenCalledWith(
        "dossier-2",
        ["moderator-2"],
        undefined,
      );
      expect(allocationActivateMock).toHaveBeenCalledWith("allocation-2", [
        {
          scopeId: "scope-2",
          reviewAssignmentIds: ["review-assignment-2"],
        },
      ]);
    });
  });
});
