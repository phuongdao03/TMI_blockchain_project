import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  CommunityCategoryManagement,
  CommunityModerationHistoryPanel,
  CommunityReportQueue,
  CommunitySettingsPanel,
  CommunityVisibilityPanel,
} from "@/components/community/community-admin-panels";

const api = vi.hoisted(() => ({
  reports: vi.fn(),
  resolveReport: vi.fn(),
  moderationHistory: vi.fn(),
  hidePost: vi.fn(),
  restorePost: vi.fn(),
  hideComment: vi.fn(),
  restoreComment: vi.fn(),
  categories: vi.fn(),
  createCategory: vi.fn(),
  updateCategory: vi.fn(),
  settings: vi.fn(),
  updateSettings: vi.fn(),
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
  api.hidePost.mockResolvedValue({
    targetType: "POST",
    targetId: "post-1",
    state: "HIDDEN",
  });
  api.restorePost.mockResolvedValue({
    targetType: "POST",
    targetId: "post-1",
    state: "VISIBLE",
  });
  api.hideComment.mockResolvedValue({
    targetType: "COMMENT",
    targetId: "comment-1",
    state: "HIDDEN",
  });
  api.restoreComment.mockResolvedValue({
    targetType: "COMMENT",
    targetId: "comment-1",
    state: "VISIBLE",
  });
  api.categories.mockResolvedValue([category]);
  api.createCategory.mockResolvedValue({ ...category, id: "category-2" });
  api.updateCategory.mockResolvedValue({ ...category, isActive: false });
  api.settings.mockResolvedValue({
    preModerationEnabled: true,
    updatedAt: "2026-10-14T09:00:00Z",
    updatedBy: "admin-1",
  });
  api.updateSettings.mockResolvedValue({
    preModerationEnabled: false,
    updatedAt: "2026-10-14T11:00:00Z",
    updatedBy: "admin-1",
  });
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

  it("hides or restores the selected post/comment with an audit reason", async () => {
    const user = userEvent.setup();
    render(<CommunityVisibilityPanel />, { wrapper });

    await user.selectOptions(screen.getByLabelText("Loại nội dung"), "COMMENT");
    await user.selectOptions(screen.getByLabelText("Thao tác"), "hide");
    await user.type(screen.getByLabelText("Mã nội dung"), "comment-1");
    await user.type(
      screen.getByLabelText("Lý do"),
      "Nội dung cần được xem xét.",
    );
    await user.click(screen.getByRole("button", { name: "Ẩn nội dung" }));
    await waitFor(() =>
      expect(api.hideComment).toHaveBeenCalledWith("comment-1", {
        reason: "Nội dung cần được xem xét.",
      }),
    );

    await user.selectOptions(screen.getByLabelText("Thao tác"), "restore");
    await user.type(
      screen.getAllByRole("textbox").at(-1)!,
      "Nội dung đã được rà soát.",
    );
    await user.click(
      screen.getByRole("button", { name: "Khôi phục nội dung" }),
    );
    await waitFor(() =>
      expect(api.restoreComment).toHaveBeenCalledWith("comment-1", {
        reason: "Nội dung đã được rà soát.",
      }),
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

  it("updates the pre-moderation setting with a required audit reason", async () => {
    const user = userEvent.setup();
    render(<CommunitySettingsPanel />, { wrapper });

    const enabled = await screen.findByRole("checkbox", {
      name: "Bật duyệt trước khi đăng",
    });
    expect((enabled as HTMLInputElement).checked).toBe(true);
    await user.click(enabled);
    await user.type(
      screen.getByLabelText("Lý do thay đổi"),
      "Đã hoàn tất giai đoạn thử nghiệm.",
    );
    await user.click(screen.getByRole("button", { name: "Lưu cài đặt" }));

    await waitFor(() =>
      expect(api.updateSettings).toHaveBeenCalledWith({
        preModerationEnabled: false,
        reason: "Đã hoàn tất giai đoạn thử nghiệm.",
      }),
    );
  });
});
