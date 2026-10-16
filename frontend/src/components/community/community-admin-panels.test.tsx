import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  CommunityCategoryManagement,
  CommunityModerationHistoryPanel,
  CommunityReportQueue,
} from "@/components/community/community-admin-panels";

const api = vi.hoisted(() => ({
  reports: vi.fn(),
  resolveReport: vi.fn(),
  moderationHistory: vi.fn(),
  categories: vi.fn(),
  createCategory: vi.fn(),
  updateCategory: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ communityAdminApi: api }));

const postReport = {
  id: "report-1",
  targetType: "POST",
  targetId: "post-1",
  status: "OPEN",
  reason: "SPAM",
  details: "Lặp lại quảng cáo.",
  createdAt: "2026-10-14T09:00:00Z",
  resolvedAt: null,
  resolutionAction: null,
  resolutionReason: null,
  reporter: {
    id: "reporter-1",
    username: "hoa",
    displayName: "Hoa",
    avatarUrl: null,
  },
  targetPreview: {
    type: "POST",
    id: "post-1",
    slug: "quang-cao",
    title: "Bài viết quảng cáo",
    excerpt: "Một đoạn giới thiệu.",
    author: {
      id: "author-1",
      username: "an",
      displayName: "An",
      avatarUrl: null,
    },
  },
};
const category = {
  id: "category-1",
  name: "Văn hóa",
  slug: "van-hoa",
  description: "Di sản và phong tục.",
  icon: null,
  sortOrder: 1,
  isActive: true,
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  api.reports.mockResolvedValue({
    success: true,
    data: [postReport],
    meta: { requestId: "reports-1", page: 1, pageSize: 20, total: 1 },
  });
  api.resolveReport.mockResolvedValue({ ...postReport, status: "RESOLVED" });
  api.moderationHistory.mockResolvedValue({
    success: true,
    data: [
      {
        id: "event-1",
        targetType: "POST",
        targetId: "post-1",
        action: "POST_HIDDEN",
        actorId: "admin-1",
        actor: {
          id: "admin-1",
          username: "admin",
          displayName: "Quản trị viên",
          avatarUrl: null,
        },
        reason: "Nội dung vi phạm.",
        requestId: "req-1",
        createdAt: "2026-10-14T10:00:00Z",
      },
    ],
    meta: { requestId: "history-1", page: 1, pageSize: 20, total: 1 },
  });
  api.categories.mockResolvedValue([category]);
  api.createCategory.mockResolvedValue({ ...category, id: "category-2" });
  api.updateCategory.mockResolvedValue({ ...category, isActive: false });
});

describe("community admin panels", () => {
  it("labels the expanded advertising and privacy report reasons", async () => {
    api.reports.mockResolvedValue({
      success: true,
      data: [
        { ...postReport, reason: "ADVERTISING" },
        { ...postReport, id: "report-privacy", reason: "PRIVACY_VIOLATION" },
      ],
      meta: {
        requestId: "reports-expanded-reasons",
        page: 1,
        pageSize: 20,
        total: 2,
      },
    });
    render(<CommunityReportQueue />, { wrapper });

    expect(await screen.findByText("Quảng cáo không phù hợp")).toBeDefined();
    expect(await screen.findByText("Xâm phạm quyền riêng tư")).toBeDefined();
  });

  it("shows safe report previews and resolves an open report with a required reason", async () => {
    const user = userEvent.setup();
    render(<CommunityReportQueue />, { wrapper });

    expect(
      await screen.findByRole("heading", { name: "Bài viết quảng cáo" }),
    ).toBeDefined();
    expect(screen.getByText("Hoa")).toBeDefined();
    await user.type(
      screen.getByLabelText("Lý do xử lý"),
      "Ẩn nội dung quảng cáo.",
    );
    await user.click(
      screen.getByRole("button", { name: "Ẩn nội dung và xử lý" }),
    );
    const dialog = await screen.findByRole("dialog", { name: "Gỡ bài viết" });
    expect(dialog.textContent).toContain("Lý do: Ẩn nội dung quảng cáo.");
    await user.click(
      within(dialog).getByRole("button", { name: "Xác nhận gỡ nội dung" }),
    );

    await waitFor(() =>
      expect(api.resolveReport).toHaveBeenCalledWith("report-1", {
        action: "HIDE",
        reason: "Ẩn nội dung quảng cáo.",
      }),
    );
  });

  it("filters and displays append-only moderation history metadata", async () => {
    const user = userEvent.setup();
    render(<CommunityModerationHistoryPanel />, { wrapper });

    expect(await screen.findByText("Nội dung vi phạm.")).toBeDefined();
    expect(screen.getByText(/req-1/)).toBeDefined();
    await user.type(screen.getByLabelText("Mã nội dung"), "post-1");
    await user.click(screen.getByRole("button", { name: "Lọc lịch sử" }));
    await waitFor(() =>
      expect(api.moderationHistory).toHaveBeenLastCalledWith(
        expect.objectContaining({ targetId: "post-1", page: 1, pageSize: 20 }),
        expect.any(AbortSignal),
      ),
    );
  });

  it("creates and edits categories with a required reason", async () => {
    const user = userEvent.setup();
    render(<CommunityCategoryManagement />, { wrapper });

    await screen.findByRole("heading", { name: "Văn hóa" });
    await user.type(screen.getByLabelText("Tên danh mục mới"), "Chuyện làng");
    await user.type(screen.getByLabelText("Slug danh mục mới"), "chuyen-lang");
    await user.type(
      screen.getByLabelText("Mô tả danh mục mới"),
      "Chuyện tại quê hương.",
    );
    await user.type(
      screen.getByLabelText("Lý do tạo danh mục"),
      "Bổ sung chủ đề mới.",
    );
    await user.click(screen.getByRole("button", { name: "Tạo danh mục" }));
    await waitFor(() =>
      expect(api.createCategory).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Chuyện làng",
          slug: "chuyen-lang",
          description: "Chuyện tại quê hương.",
          reason: "Bổ sung chủ đề mới.",
        }),
      ),
    );

    await user.click(
      screen.getByRole("button", { name: "Chỉnh sửa danh mục: Văn hóa" }),
    );
    await user.clear(screen.getByLabelText("Lý do cập nhật danh mục"));
    await user.type(
      screen.getByLabelText("Lý do cập nhật danh mục"),
      "Tạm ngừng chủ đề.",
    );
    await user.click(screen.getByRole("button", { name: "Lưu danh mục" }));
    await waitFor(() =>
      expect(api.updateCategory).toHaveBeenCalledWith(
        "category-1",
        expect.objectContaining({
          reason: "Tạm ngừng chủ đề.",
        }),
      ),
    );
  });
});
