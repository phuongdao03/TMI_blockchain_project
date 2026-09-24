import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkAllocationWorkspace } from "@/components/work-allocations/work-allocation-workspace";

const listMock = vi.hoisted(() => vi.fn());
const createMock = vi.hoisted(() => vi.fn());
const staffListMock = vi.hoisted(() => vi.fn());
const dossierListMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  workAllocationAdminApi: {
    list: listMock,
    create: createMock,
  },
  staffAccountsApi: {
    list: staffListMock,
  },
  adminReviewApi: {
    list: dossierListMock,
  },
}));

describe("WorkAllocationWorkspace", () => {
  it("creates a general allocation with an explicit responsible person", async () => {
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
    fireEvent.click(screen.getByRole("button", { name: "Tạo phân công" }));
    fireEvent.change(screen.getByLabelText("Mục tiêu công việc"), {
      target: { value: "Rà soát kế hoạch truyền thông" },
    });
    fireEvent.click(await screen.findByLabelText("linh.tran@example.com"));
    fireEvent.click(screen.getByRole("button", { name: "Lưu phân công" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith({
        kind: "GENERIC",
        objective: "Rà soát kế hoạch truyền thông",
        description: null,
        dueAt: null,
        priority: "MEDIUM",
        members: [{ userId: "moderator-1", responsibility: "CONTRIBUTOR" }],
      });
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
      data: [],
      meta: { page: 1, pageSize: 50, total: 0 },
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
      await screen.findByRole("button", { name: "Tạo phân công" }),
    );
    fireEvent.click(screen.getByRole("tab", { name: "Hồ sơ thẩm định" }));

    expect(
      await screen.findByRole("heading", { name: "Phân công hồ sơ thẩm định" }),
    ).toBeDefined();
  });
});
