import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MyWorkAllocationList } from "@/components/work-allocations/my-work-allocation-list";

const listMock = vi.hoisted(() => vi.fn());
const reviewListMock = vi.hoisted(() => vi.fn());

vi.mock("next/link", () => ({ default: "a" }));

vi.mock("@/lib/api/client", () => ({
  workAllocationSelfApi: {
    list: listMock,
  },
  reviewApi: { list: reviewListMock },
}));

describe("MyWorkAllocationList", () => {
  it("shows legacy reviewer assignments even when no work allocation was created", async () => {
    listMock.mockResolvedValue({ data: [], meta: { total: 0 } });
    reviewListMock.mockResolvedValue({
      data: [
        {
          assignment: { id: "review-1", status: "ASSIGNED" },
          dossierCode: "HS-2026-01",
          dossierTitle: "Hồ sơ chờ thẩm định",
          versionNo: 1,
        },
      ],
      meta: { total: 1 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MyWorkAllocationList />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Hồ sơ chờ thẩm định")).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Bắt đầu thẩm định: Hồ sơ chờ thẩm định" })
        .getAttribute("href"),
    ).toBe("/reviews/review-1");
    expect(screen.queryByText("Chưa có công việc được giao")).toBeNull();
    expect(screen.getByText("Mới được giao")).toBeDefined();
  });

  it("separates submitted reviews from work that still needs attention", async () => {
    listMock.mockResolvedValue({ data: [], meta: { total: 0 } });
    reviewListMock.mockResolvedValue({
      data: [
        {
          assignment: { id: "open", status: "IN_PROGRESS", dueAt: null },
          dossierCode: "HS-1",
          dossierTitle: "Hồ sơ đang làm",
          versionNo: 1,
        },
        {
          assignment: { id: "done", status: "SUBMITTED", dueAt: null },
          dossierCode: "HS-2",
          dossierTitle: "Hồ sơ đã gửi",
          versionNo: 2,
        },
      ],
      meta: { total: 2 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MyWorkAllocationList />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Hồ sơ đang làm")).toBeDefined();
    expect(screen.queryByText("Hồ sơ đã gửi")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Đã kết thúc" }));
    expect(screen.getByText("Hồ sơ đã gửi")).toBeDefined();
    expect(screen.getByText("Đã gửi kết quả")).toBeDefined();
    expect(screen.queryByText("Hồ sơ đang làm")).toBeNull();
  });

  it("does not show the same dossier twice when an allocation and a review exist", async () => {
    listMock.mockResolvedValue({
      data: [
        {
          id: "allocation-1",
          kind: "DOSSIER_REVIEW",
          objective: "Thẩm định hồ sơ",
          dossierId: "dossier-1",
          dossierVersionId: "version-1",
          status: "ACTIVE",
          priority: "MEDIUM",
          dueAt: null,
        },
      ],
      meta: { total: 1 },
    });
    reviewListMock.mockResolvedValue({
      data: [
        {
          assignment: {
            id: "review-1",
            dossierId: "dossier-1",
            dossierVersionId: "version-1",
            status: "ASSIGNED",
            dueAt: null,
          },
          dossierCode: "HS-1",
          dossierTitle: "Hồ sơ A",
          versionNo: 1,
        },
      ],
      meta: { total: 1 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MyWorkAllocationList />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Hồ sơ A")).toBeDefined();
    expect(screen.queryByText("Thẩm định hồ sơ")).toBeNull();
  });

  it("shows a moderator's assigned work and connects dossier work to review", async () => {
    reviewListMock.mockResolvedValue({ data: [], meta: { total: 0 } });
    listMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "allocation-1",
          kind: "GENERIC",
          objective: "Rà soát kế hoạch truyền thông",
          description: null,
          dossierId: null,
          dossierVersionId: null,
          dueAt: null,
          priority: "MEDIUM",
          status: "ACTIVE",
          createdByUserId: "admin-1",
          createdAt: "2026-09-22T08:00:00Z",
          updatedAt: "2026-09-22T08:00:00Z",
        },
        {
          id: "allocation-2",
          kind: "DOSSIER_REVIEW",
          objective: "Thẩm định hồ sơ HS-2026-01",
          description: null,
          dossierId: "dossier-1",
          dossierVersionId: "version-1",
          dueAt: null,
          priority: "HIGH",
          status: "ACTIVE",
          createdByUserId: "admin-1",
          createdAt: "2026-09-22T08:00:00Z",
          updatedAt: "2026-09-22T08:00:00Z",
        },
      ],
      meta: { page: 1, pageSize: 50, total: 2 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <MyWorkAllocationList />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: "Công việc được giao" }),
    ).toBeDefined();
    expect(
      await screen.findByText("Rà soát kế hoạch truyền thông"),
    ).toBeDefined();
    expect(screen.getByText("Thẩm định hồ sơ HS-2026-01")).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Mở hàng đợi thẩm định" })
        .getAttribute("href"),
    ).toBe("/reviews");
  });
});
