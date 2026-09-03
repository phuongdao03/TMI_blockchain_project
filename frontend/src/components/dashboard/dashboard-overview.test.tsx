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
    email: "user@tmigroup.vn",
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
      pagination: { page: 1, pageSize: 5, total: 0, totalPages: 1 },
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
});
