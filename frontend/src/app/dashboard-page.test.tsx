import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("shows the preview dashboard without loading business data", () => {
    vi.stubEnv("NEXT_PUBLIC_RELEASE_MODE", "preview");
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <AuthUserProvider
          user={{
            id: "preview-user",
            email: "preview@tmigroup.vn",
            roles: ["APPLICANT"],
            accountType: "INDIVIDUAL_APPLICANT",
          }}
        >
          <DashboardPage />
        </AuthUserProvider>
      </QueryClientProvider>,
    );

    expect(screen.getByText("Không gian của bạn")).toBeDefined();
    expect(screen.getByRole("link", { name: /Xem thư viện/ })).toBeDefined();
    expect(
      screen.getByRole("link", { name: /Tìm hiểu cách tham gia/i }),
    ).toBeDefined();
    expect(screen.queryByText(/Phiên bản trải nghiệm/i)).toBeNull();
    expect(screen.queryByText("Tạo hồ sơ mới")).toBeNull();
    expect(listMock).not.toHaveBeenCalled();
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
        name: "Việc cần làm",
      }),
    ).toBeDefined();
    expect(screen.getByRole("link", { name: "Tạo hồ sơ mới" })).toBeDefined();
    expect(await screen.findByText("Chưa có hồ sơ")).toBeDefined();
    expect(screen.getByText("Cập nhật gần nhất")).toBeDefined();
  });

  it.each([
    ["DRAFT", "Tiếp tục hoàn thiện hồ sơ", "/dossiers/dossier-1"],
    ["UNDER_REVIEW", "Xem tiến độ hồ sơ", "/dossiers/dossier-1"],
    ["PAYMENT_PENDING", "Thanh toán phí phát hành", "/dossiers/dossier-1"],
    ["CERTIFICATE_ISSUED", "Tải chứng thư", "/certificates"],
  ] as const)(
    "uses the correct primary action for %s",
    async (status, label, href) => {
      listMock.mockResolvedValue({
        success: true,
        data: [
          {
            id: "dossier-1",
            code: "TMI-001",
            ownerUserId: "applicant-1",
            organizationId: null,
            categoryId: "category-1",
            title: "Tác phẩm thử nghiệm",
            slug: null,
            summary: null,
            status,
            visibility: "PRIVATE",
            currentVersionNo: 1,
            submittedAt: null,
            createdAt: "2026-08-01T00:00:00Z",
            updatedAt: "2026-08-08T00:00:00Z",
            canEdit: status === "DRAFT",
          },
        ],
        meta: { requestId: "test", page: 1, pageSize: 5, total: 1 },
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

      const actions = await screen.findAllByRole("link", { name: label });
      expect(actions).toHaveLength(1);
      expect(actions[0]?.getAttribute("href")).toBe(href);
    },
  );

  it("offers a recovery action when dossiers cannot be loaded", async () => {
    listMock.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({
      success: true,
      data: [],
      meta: { requestId: "retry", page: 1, pageSize: 5, total: 0 },
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

    expect(await screen.findByText("Chưa thể tải hồ sơ")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    expect(await screen.findByText("Chưa có hồ sơ")).toBeDefined();
    expect(listMock).toHaveBeenCalledTimes(2);
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
      screen.getByRole("heading", { level: 1, name: "Khám phá đề cử" }),
    ).toBeDefined();
    expect(screen.queryByRole("link", { name: "Tạo hồ sơ mới" })).toBeNull();
    expect(listMock).not.toHaveBeenCalled();
  });
});
