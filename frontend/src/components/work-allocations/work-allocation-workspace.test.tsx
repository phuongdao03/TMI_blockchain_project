import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkAllocationWorkspace } from "@/components/work-allocations/work-allocation-workspace";

const listMock = vi.hoisted(() => vi.fn());
const createMock = vi.hoisted(() => vi.fn());
const activateMock = vi.hoisted(() => vi.fn());
const staffListMock = vi.hoisted(() => vi.fn());
const dossierListMock = vi.hoisted(() => vi.fn());
const dossierGetMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  workAllocationAdminApi: {
    list: listMock,
    create: createMock,
    activate: activateMock,
  },
  staffAccountsApi: {
    list: staffListMock,
  },
  adminReviewApi: {
    list: dossierListMock,
    get: dossierGetMock,
  },
}));

describe("WorkAllocationWorkspace", () => {
  it("creates a general allocation with an explicit responsible person", async () => {
    dossierListMock.mockResolvedValue({
      data: [],
      meta: { total: 0 },
    });
    listMock.mockResolvedValue({
      success: true,
      data: [],
      meta: { page: 1, pageSize: 20, total: 0 },
    });
    staffListMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "moderator-1",
          email: "linh.tran@example.com",
          role: "MODERATOR",
          status: "ACTIVE",
          createdAt: null,
          lastLoginAt: null,
        },
      ],
      meta: { page: 1, pageSize: 100, total: 1 },
    });
    createMock.mockResolvedValue({ id: "allocation-1" });
    activateMock.mockResolvedValue({ id: "allocation-1", status: "ACTIVE" });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <WorkAllocationWorkspace />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: "Phân công công việc" }),
    ).toBeDefined();
    fireEvent.click(
      screen.getByRole("button", { name: "Giao hồ sơ thẩm định" }),
    );
    fireEvent.click(screen.getByRole("tab", { name: "Công việc chung" }));
    fireEvent.change(screen.getByLabelText("Mục tiêu công việc"), {
      target: { value: "Rà soát kế hoạch truyền thông" },
    });
    fireEvent.click(await screen.findByLabelText("linh.tran@example.com"));
    fireEvent.click(screen.getByRole("button", { name: "Giao công việc" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith({
        kind: "GENERIC",
        objective: "Rà soát kế hoạch truyền thông",
        description: null,
        dueAt: null,
        priority: "MEDIUM",
        members: [{ userId: "moderator-1", responsibility: "CONTRIBUTOR" }],
      });
      expect(activateMock).toHaveBeenCalledWith("allocation-1", []);
    });
  });

  it("opens the dossier composer from the unified allocation workspace", async () => {
    listMock.mockResolvedValue({
      success: true,
      data: [],
      meta: { page: 1, pageSize: 20, total: 0 },
    });
    staffListMock.mockResolvedValue({
      success: true,
      data: [],
      meta: { page: 1, pageSize: 100, total: 0 },
    });
    dossierListMock.mockResolvedValue({
      success: true,
      data: [
        {
          dossierId: "dossier-1",
          dossierCode: "HS-2026-01",
          dossierTitle: "Đồng Diễn Múa Saravan",
          status: "SUBMITTED",
          versionNo: 1,
          submittedAt: "2026-10-05T08:00:00Z",
          assignmentCount: 0,
        },
      ],
      meta: { page: 1, pageSize: 100, total: 1 },
    });
    dossierGetMock.mockResolvedValue({
      dossierId: "dossier-1",
      dossierCode: "HS-2026-01",
      dossierTitle: "Đồng Diễn Múa Saravan",
      status: "SUBMITTED",
      versionNo: 1,
      snapshotJson: { evidences: [] },
      assignments: [],
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <WorkAllocationWorkspace />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Đồng Diễn Múa Saravan")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Giao hồ sơ" }));

    expect(
      await screen.findByRole("heading", { name: "Phân công hồ sơ thẩm định" }),
    ).toBeDefined();
    expect(
      (screen.getByLabelText("Hồ sơ cần thẩm định") as HTMLSelectElement).value,
    ).toBe("dossier-1");
  });
});
