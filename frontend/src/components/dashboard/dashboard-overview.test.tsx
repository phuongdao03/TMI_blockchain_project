import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardOverview } from "@/components/dashboard/dashboard-overview";

const { listDossiers } = vi.hoisted(() => ({
  listDossiers: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  dossierApi: { list: listDossiers },
}));

vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => ({
    id: "user-1",
    email: "user@cnsgroup.vn",
    roles: ["USER"],
    accountType: "INDIVIDUAL_APPLICANT",
  }),
}));

function renderDashboard() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <DashboardOverview />
    </QueryClientProvider>,
  );
}

describe("DashboardOverview", () => {
  beforeEach(() => {
    listDossiers.mockReset();
  });

  it("skips priority queries when a new account has no dossiers", async () => {
    listDossiers.mockResolvedValue({
      data: [],
      meta: { page: 1, pageSize: 5, total: 0 },
    });
    renderDashboard();
    await screen.findByRole("link", { name: /Tạo hồ sơ mới/ });
    expect(listDossiers).toHaveBeenCalledTimes(1);
    expect(listDossiers).toHaveBeenCalledWith(
      expect.not.objectContaining({ status: expect.anything() }),
    );
  });

  it("finds older tasks outside the recent page and prioritizes supplementation", async () => {
    const dossier = (id: string, status: string) => ({
      id,
      status,
      code: `THV-${id}`,
      title: id,
      updatedAt: "2026-10-01T00:00:00Z",
    });
    listDossiers.mockImplementation(async (filters) => ({
      data:
        filters.status === "NEEDS_SUPPLEMENT"
          ? [dossier("older-supplement", "NEEDS_SUPPLEMENT")]
          : filters.status === "PAYMENT_PENDING"
            ? [dossier("older-payment", "PAYMENT_PENDING")]
            : filters.status === "DRAFT"
              ? [dossier("draft-1", "DRAFT"), dossier("draft-2", "DRAFT")]
              : [dossier("recent-review", "UNDER_REVIEW")],
      meta: { page: 1, pageSize: 5, total: 10 },
    }));
    renderDashboard();
    const tasks = await screen.findByRole("region", { name: "Cần bạn xử lý" });
    await waitFor(() =>
      expect(within(tasks).getAllByRole("link")).toHaveLength(3),
    );
    expect(
      within(tasks)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual([
      "/dossiers/older-supplement",
      "/dossiers/older-payment",
      "/dossiers/draft-1",
    ]);
    expect(screen.queryByText("Thanh toán phí phát hành")).toBeNull();
    expect(screen.queryByText("Trạng thái dễ hiểu")).toBeNull();
  });

  it("does not show an action panel when all dossiers are being processed", async () => {
    listDossiers.mockImplementation(async (filters) => ({
      data: filters.status
        ? []
        : [
            {
              id: "review",
              title: "Hồ sơ đang thẩm định",
              code: "THV-2",
              status: "UNDER_REVIEW",
              updatedAt: "2026-10-20T00:00:00Z",
            },
          ],
      meta: { page: 1, pageSize: 5, total: filters.status ? 0 : 1 },
    }));
    renderDashboard();
    expect(await screen.findByText("Hồ sơ đang thẩm định")).toBeDefined();
    expect(screen.queryByRole("region", { name: "Cần bạn xử lý" })).toBeNull();
    expect(screen.getByText(/Xem tiến độ hồ sơ/)).toBeDefined();
    expect(screen.getByText(/20\/10\/2026/)).toBeDefined();
  });

  it("offers recovery when actionable dossiers fail without hiding recent dossiers", async () => {
    listDossiers.mockImplementation(async (filters) => {
      if (filters.status) throw new Error("task lookup unavailable");
      return {
        data: [
          {
            id: "recent",
            title: "Hồ sơ còn xem được",
            code: "THV-3",
            status: "UNDER_REVIEW",
            updatedAt: "2026-10-20T00:00:00Z",
          },
        ],
        meta: { page: 1, pageSize: 5, total: 1 },
      };
    });
    renderDashboard();
    expect(
      await screen.findByRole("button", { name: "Tải lại việc cần làm" }),
    ).toBeDefined();
    expect(screen.getByText("Hồ sơ còn xem được")).toBeDefined();
  });

  it("uses a readable skeleton while dossiers are loading", () => {
    listDossiers.mockReturnValue(new Promise(() => undefined));

    const { container } = renderDashboard();

    expect(screen.getByText("Đang tải hồ sơ của bạn…")).toBeDefined();
    expect(container.querySelectorAll(".dashboard-skeleton")).toHaveLength(3);
    expect(container.querySelector(".thv-loading-spinner")).not.toBeNull();
    expect(screen.queryByRole("link", { name: /Tạo hồ sơ mới/ })).toBeNull();
    expect(container.querySelector('a[href="/dossiers/new"]')).toBeNull();
  });

  it("shows a task-focused empty state with one primary action", async () => {
    listDossiers.mockResolvedValue({
      data: [],
      meta: { page: 1, pageSize: 5, total: 0 },
    });

    renderDashboard();

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Bắt đầu hồ sơ đầu tiên" }),
      ).toBeDefined();
    });
    expect(screen.getByRole("link", { name: /Tạo hồ sơ mới/i })).toBeDefined();
    expect(screen.getByText(/Chọn loại hồ sơ phù hợp/i)).toBeDefined();
    expect(screen.queryByText("0")).toBeNull();
    expect(screen.queryByText("Trạng thái của hồ sơ gần đây")).toBeNull();
    expect(
      screen.getByRole("heading", { level: 1, name: "Việc cần làm" }),
    ).toBeDefined();
  });

  it("uses the server total without inventing global status counts", async () => {
    listDossiers.mockResolvedValue({
      data: [
        {
          id: "recent-1",
          code: "THV-1",
          title: "Hồ sơ gần đây",
          status: "DRAFT",
          updatedAt: "2026-10-01T00:00:00Z",
        },
      ],
      meta: { page: 1, pageSize: 5, total: 27 },
    });

    renderDashboard();

    expect(await screen.findByText("Tổng cộng 27 hồ sơ")).toBeDefined();
    expect(screen.queryByText("Trạng thái của hồ sơ gần đây")).toBeNull();
    expect(screen.queryByText("Bằng xác lập sẵn sàng")).toBeNull();
  });

  it("keeps the create action disabled when loading dossiers fails", async () => {
    listDossiers.mockRejectedValue(new Error("network unavailable"));

    renderDashboard();

    expect(
      await screen.findByText("Chưa thể tải hồ sơ của bạn. Vui lòng thử lại."),
    ).toBeDefined();
    expect(screen.queryByRole("link", { name: /Tạo hồ sơ mới/ })).toBeNull();
    expect(
      screen.getByRole("button", { name: "Tải lại danh sách" }),
    ).toBeDefined();
    expect(screen.queryByRole("link", { name: "Gửi đề cử mới" })).toBeNull();
    expect(document.querySelector('a[href="/dossiers/new"]')).toBeNull();
  });
});
