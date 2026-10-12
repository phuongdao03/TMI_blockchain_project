import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkAllocationWorkspace } from "@/components/work-allocations/work-allocation-workspace";

const listMock = vi.hoisted(() => vi.fn());
const createMock = vi.hoisted(() => vi.fn());
const activateMock = vi.hoisted(() => vi.fn());
const completeMock = vi.hoisted(() => vi.fn());
const cancelMock = vi.hoisted(() => vi.fn());
const getMock = vi.hoisted(() => vi.fn());
const staffListMock = vi.hoisted(() => vi.fn());
const dossierListMock = vi.hoisted(() => vi.fn());
const dossierGetMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  workAllocationAdminApi: {
    list: listMock,
    create: createMock,
    activate: activateMock,
    complete: completeMock,
    cancel: cancelMock,
    get: getMock,
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
  it("closes active work and moves it out of the open queue", async () => {
    const active = {
      id: "allocation-1",
      kind: "GENERIC",
      objective: "Lập báo cáo",
      description: null,
      dossierId: null,
      dossierVersionId: null,
      dueAt: null,
      priority: "MEDIUM",
      status: "ACTIVE",
      createdByUserId: "admin-1",
      createdAt: "2026-10-01T00:00:00Z",
      updatedAt: "2026-10-01T00:00:00Z",
    };
    let currentStatus = "ACTIVE";
    listMock.mockImplementation(({ state }: { state: string }) =>
      Promise.resolve({
        data:
          (state === "OPEN" && currentStatus === "ACTIVE") ||
          (state === "COMPLETED" && currentStatus === "COMPLETED")
            ? [{ ...active, status: currentStatus }]
            : [],
        meta: { total: 1 },
      }),
    );
    staffListMock.mockResolvedValue({ data: [], meta: { total: 0 } });
    dossierListMock.mockResolvedValue({ data: [], meta: { total: 0 } });
    completeMock.mockImplementation(async () => {
      currentStatus = "COMPLETED";
      return { ...active, status: "COMPLETED" };
    });
    getMock.mockResolvedValue({
      ...active,
      status: "COMPLETED",
      members: [],
      scopes: [],
      scopeCoverage: [],
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <WorkAllocationWorkspace />
      </QueryClientProvider>,
    );
    fireEvent.click(
      await screen.findByRole("button", { name: "Đánh dấu hoàn thành" }),
    );
    expect(completeMock).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole("button", { name: "Xác nhận hoàn thành" }),
    );
    await waitFor(() =>
      expect(completeMock).toHaveBeenCalledWith("allocation-1"),
    );
    await waitFor(() =>
      expect(listMock).toHaveBeenCalledWith({
        pageSize: 50,
        state: "COMPLETED",
      }),
    );
    expect(await screen.findByText("Hoàn thành")).toBeDefined();
    expect(
      screen.queryByRole("button", { name: "Đánh dấu hoàn thành" }),
    ).toBeNull();
  });
  it("keeps active work visible and explains a failed completion", async () => {
    listMock.mockResolvedValue({
      data: [
        {
          id: "allocation-2",
          kind: "GENERIC",
          objective: "Duyệt hồ sơ",
          description: null,
          dossierId: null,
          dossierVersionId: null,
          dueAt: null,
          priority: "MEDIUM",
          status: "ACTIVE",
          createdByUserId: "admin-1",
          createdAt: "2026-10-01T00:00:00Z",
          updatedAt: "2026-10-01T00:00:00Z",
        },
      ],
      meta: { total: 1 },
    });
    staffListMock.mockResolvedValue({ data: [], meta: { total: 0 } });
    dossierListMock.mockResolvedValue({ data: [], meta: { total: 0 } });
    completeMock.mockRejectedValue(new Error("Network unavailable"));
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <WorkAllocationWorkspace />
      </QueryClientProvider>,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "Đánh dấu hoàn thành" }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Xác nhận hoàn thành" }),
    );

    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      expect.stringContaining("Chưa cập nhật được trạng thái"),
    );
    expect(screen.getByText("Đang thực hiện")).toBeDefined();
    expect(
      screen.getByRole("button", { name: "Đánh dấu hoàn thành" }),
    ).toBeDefined();
  });
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
        {
          id: "moderator-2",
          email: "mai.nguyen@example.com",
          role: "MODERATOR",
          status: "ACTIVE",
          createdAt: null,
          lastLoginAt: null,
        },
      ],
      meta: { page: 1, pageSize: 100, total: 2 },
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
    fireEvent.click(screen.getByLabelText("mai.nguyen@example.com"));
    fireEvent.change(screen.getByLabelText("Người phụ trách chính"), {
      target: { value: "moderator-2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Giao công việc" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith({
        kind: "GENERIC",
        objective: "Rà soát kế hoạch truyền thông",
        description: null,
        dueAt: null,
        priority: "MEDIUM",
        members: [
          { userId: "moderator-1", responsibility: "CONTRIBUTOR" },
          { userId: "moderator-2", responsibility: "LEAD" },
        ],
      });
      expect(activateMock).toHaveBeenCalledWith("allocation-1", []);
    });
    expect(
      await screen.findByText("Đã giao công việc cho nhân viên"),
    ).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: "Theo dõi công việc" })
        .getAttribute("href"),
    ).toBe("#allocation-list");
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
