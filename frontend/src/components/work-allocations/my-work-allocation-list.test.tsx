import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MyWorkAllocationList } from "@/components/work-allocations/my-work-allocation-list";

const listMock = vi.hoisted(() => vi.fn());
const reviewListMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  workAllocationSelfApi: {
    list: listMock,
  },
  reviewApi: { list: reviewListMock },
}));

describe("MyWorkAllocationList", () => {
  it("shows legacy reviewer assignments even when no work allocation was created", async () => {
    listMock.mockResolvedValue({ data: [], meta: { total: 0 } });
    reviewListMock.mockResolvedValue({ data: [{
      assignment: { id: "review-1", status: "ASSIGNED" },
      dossierCode: "HS-2026-01", dossierTitle: "Hồ sơ chờ thẩm định", versionNo: 1,
    }], meta: { total: 1 } });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MyWorkAllocationList /></QueryClientProvider>);
    expect(await screen.findByText("Hồ sơ chờ thẩm định")).toBeDefined();
    expect(screen.getByRole("link", { name: "Mở hồ sơ thẩm định" }).getAttribute("href")).toBe("/reviews/review-1");
    expect(screen.queryByText("Chưa có công việc được giao")).toBeNull();
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
