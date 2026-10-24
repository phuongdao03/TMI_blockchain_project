import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReviewAssignmentList } from "@/components/reviews/review-assignment-list";

const listMock = vi.hoisted(() => vi.fn());

vi.mock("next/link", () => ({ default: "a" }));

vi.mock("@/lib/api/client", () => ({
  reviewApi: { list: listMock },
}));

describe("ReviewAssignmentList", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("marks a deadline overdue as time passes without refetching", async () => {
    const now = vi
      .spyOn(Date, "now")
      .mockReturnValue(Date.parse("2026-08-08T07:59:45Z"));
    listMock.mockResolvedValue({
      data: [
        {
          assignment: {
            id: "due-soon",
            status: "IN_PROGRESS",
            dueAt: "2026-08-08T08:00:00Z",
          },
          dossierCode: "CNS-3",
          dossierTitle: "Hồ sơ sắp đến hạn",
          versionNo: 1,
        },
      ],
      meta: { page: 1, pageSize: 10, total: 1 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const view = render(
      <QueryClientProvider client={client}>
        <ReviewAssignmentList page={1} pageSize={10} />
      </QueryClientProvider>,
    );

    await screen.findByText("Hồ sơ sắp đến hạn");
    expect(screen.queryByText("Trễ hạn")).toBeNull();
    now.mockReturnValue(Date.parse("2026-08-08T08:00:15Z"));
    act(() => {
      window.dispatchEvent(new Event("focus"));
    });
    expect(screen.getByText("Trễ hạn")).toBeDefined();
    expect(listMock).toHaveBeenCalledTimes(1);
    view.unmount();
  });

  it("renders the reviewer queue and assignment action", async () => {
    listMock.mockResolvedValue({
      success: true,
      data: [
        {
          assignment: {
            id: "4155dbf5-bb3e-449d-8bf0-9572cc642cac",
            dossierId: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
            dossierVersionId: "8155dbf5-bb3e-449d-8bf0-9572cc642cac",
            reviewerUserId: "7155dbf5-bb3e-449d-8bf0-9572cc642cac",
            assignedBy: "6155dbf5-bb3e-449d-8bf0-9572cc642cac",
            dueAt: "2026-08-08T08:00:00Z",
            status: "IN_PROGRESS",
            conflictDeclaredAt: null,
            conflictReason: null,
          },
          dossierCode: "HS-2026-000001",
          dossierTitle: "Hồ sơ thương hiệu CNS",
          versionNo: 1,
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 10, total: 1 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <ReviewAssignmentList page={1} pageSize={10} status="IN_PROGRESS" />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Hồ sơ thương hiệu CNS")).toBeDefined();
    expect(screen.getByText("Đang thẩm định")).toBeDefined();
    expect(screen.getByText("Công việc cần xử lý")).toBeDefined();
    expect(screen.getByText("1 hồ sơ trong hàng đợi")).toBeDefined();
    expect(screen.queryByText(/Bước tiếp theo:/)).toBeNull();
    expect(screen.queryByText(/xung đột lợi ích/i)).toBeNull();
    expect(
      screen
        .getByRole("link", { name: "Tiếp tục thẩm định" })
        .getAttribute("href"),
    ).toBe("/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac");
  });

  it("puts overdue active work first on the current page", async () => {
    listMock.mockResolvedValue({
      data: [
        {
          assignment: { id: "finished", status: "SUBMITTED", dueAt: null },
          dossierCode: "CNS-1",
          dossierTitle: "Việc đã xong",
          versionNo: 1,
        },
        {
          assignment: {
            id: "overdue",
            status: "IN_PROGRESS",
            dueAt: "2020-01-01T00:00:00Z",
          },
          dossierCode: "CNS-2",
          dossierTitle: "Việc trễ hạn",
          versionNo: 1,
        },
      ],
      meta: { page: 1, pageSize: 10, total: 2 },
    });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ReviewAssignmentList page={1} pageSize={10} />
      </QueryClientProvider>,
    );

    await screen.findByText("Việc trễ hạn");
    expect(screen.getByText("Trễ hạn")).toBeDefined();
    expect(
      screen.getAllByRole("article").map((item) => item.textContent),
    ).toEqual([
      expect.stringContaining("Việc trễ hạn"),
      expect.stringContaining("Việc đã xong"),
    ]);
  });
});
