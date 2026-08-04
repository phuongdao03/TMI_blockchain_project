import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/(dashboard)/dashboard/page";
import { AuthUserProvider } from "@/lib/auth/user-context";

const listMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  dossierApi: { list: listMock },
}));

describe("dashboard overview", () => {
  beforeEach(() => {
    listMock.mockReset();
  });

  it("renders live dossier summary and primary applicant action", async () => {
    listMock.mockResolvedValue({
      success: true,
      data: [],
      meta: { requestId: "test", page: 1, pageSize: 5, total: 0 },
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <AuthUserProvider
          user={{
            id: "applicant-1",
            email: "owner@tmigroup.vn",
            roles: ["APPLICANT"],
            accountType: "INDIVIDUAL_APPLICANT",
          }}
        >
          <DashboardPage />
        </AuthUserProvider>
      </QueryClientProvider>,
    );

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Tổng quan xác lập",
      }),
    ).toBeDefined();
    expect(screen.getByRole("link", { name: "Tạo hồ sơ mới" })).toBeDefined();
    expect(await screen.findByText("Chưa có hồ sơ")).toBeDefined();
    expect(screen.getByText("Nền tảng tin cậy")).toBeDefined();
  });

  it("keeps dossier actions out of the public-user landing page", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <AuthUserProvider
          user={{
            id: "public-user-1",
            email: "viewer@tmigroup.vn",
            roles: ["PUBLIC_USER"],
            accountType: "PUBLIC_USER",
          }}
        >
          <DashboardPage />
        </AuthUserProvider>
      </QueryClientProvider>,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: "Khám phá TMI" }),
    ).toBeDefined();
    expect(screen.queryByRole("link", { name: "Tạo hồ sơ mới" })).toBeNull();
    expect(listMock).not.toHaveBeenCalled();
  });
});
