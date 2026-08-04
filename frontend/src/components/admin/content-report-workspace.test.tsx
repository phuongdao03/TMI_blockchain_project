import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ContentReportWorkspace } from "@/components/admin/content-report-workspace";
import { contentReportAdminApi } from "@/lib/api/client";
import type { ContentReportAdmin } from "@/lib/api/types";

vi.mock("@/lib/api/client", () => ({
  contentReportAdminApi: {
    list: vi.fn(),
    suspend: vi.fn(),
    transition: vi.fn(),
  },
}));

const report: ContentReportAdmin = {
  id: "105ac997-68a2-40d1-8194-a2181d0a9c32",
  publicWorkId: "a1e8dfb7-a24d-4b8b-b158-98a2cc7dd0b9",
  workTitle: "Tác phẩm cần kiểm tra",
  workSlug: "tac-pham-can-kiem-tra",
  workVersion: 4,
  reason: "COPYRIGHT",
  description: "Mô tả báo cáo không chứa danh tính.",
  status: "OPEN",
  reporterType: "ANONYMOUS",
  hasContactEmail: true,
  assignedToUserId: null,
  resolutionNote: null,
  resolvedAt: null,
  createdAt: "2026-08-01T00:00:00Z",
  updatedAt: "2026-08-01T00:00:00Z",
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.mocked(contentReportAdminApi.list).mockResolvedValue({
    success: true,
    data: [report],
    meta: { request_id: "report-list", page: 1, pageSize: 20, total: 1 },
  });
  vi.mocked(contentReportAdminApi.transition).mockResolvedValue({
    ...report,
    status: "UNDER_REVIEW",
  });
});

describe("ContentReportWorkspace", () => {
  it("shows a privacy-safe queue and lets an admin claim a report", async () => {
    const user = userEvent.setup();
    render(<ContentReportWorkspace />, { wrapper });
    expect(await screen.findByText(report.workTitle)).toBeTruthy();
    expect(screen.getByText(/Ẩn danh · Có email mã hóa/)).toBeTruthy();
    expect(screen.queryByText(/reporter@/)).toBeNull();
    await user.click(screen.getByRole("button", { name: "Nhận xử lý" }));
    await waitFor(() =>
      expect(contentReportAdminApi.transition).toHaveBeenCalledWith(
        report.id,
        "UNDER_REVIEW",
        null,
      ),
    );
  });
});
