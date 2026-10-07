import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
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

  it("uses a readable skeleton while dossiers are loading", () => {
    listDossiers.mockReturnValue(new Promise(() => undefined));

    const { container } = renderDashboard();

    expect(screen.getByRole("status").textContent).toContain("Đang tải hồ sơ");
    expect(container.querySelectorAll(".dashboard-skeleton")).toHaveLength(3);
  });

  it("shows a task-focused empty state with one primary action", async () => {
    listDossiers.mockResolvedValue({
      data: [],
      meta: { page: 1, pageSize: 5, total: 0 },
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("Chưa có hồ sơ")).toBeDefined();
    });
    expect(screen.getByRole("link", { name: /Tạo hồ sơ mới/i })).toBeDefined();
    expect(
      screen.getByRole("heading", { level: 1, name: "Việc cần làm" }),
    ).toBeDefined();
  });

  it("states that status counts cover only recently loaded dossiers", async () => {
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
    expect(screen.getByText("Trạng thái của hồ sơ gần đây")).toBeDefined();
    expect(
      screen.getByText("Số liệu dưới đây chỉ tính trên 1 hồ sơ vừa tải."),
    ).toBeDefined();
  });
});
