import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GuideArticleWorkspace } from "@/components/admin/guide-article-workspace";
import { guideApi } from "@/lib/api/client";
import type { CmsGuideArticle } from "@/lib/api/types";

const article: CmsGuideArticle = {
  id: "guide-1",
  title: "Tìm và xem đề cử đã công bố",
  slug: "explore-nominations",
  summary: "Hướng dẫn xem nội dung công khai.",
  category: "getting-started",
  audiences: ["PUBLIC"],
  bodyHtml: "<h2>Mở thư viện</h2><p>Chọn nội dung.</p>",
  status: "DRAFT",
  sortOrder: 10,
  version: 1,
  readingMinutes: 1,
  publishedAt: null,
  createdAt: "2026-10-18T00:00:00Z",
  updatedAt: "2026-10-18T00:00:00Z",
};

function renderWorkspace() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>
      <GuideArticleWorkspace />
    </QueryClientProvider>,
  );
}

describe("GuideArticleWorkspace", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(guideApi, "adminList").mockResolvedValue({
      success: true,
      data: [article],
      meta: { page: 1, pageSize: 20, total: 1 },
    });
    vi.spyOn(guideApi, "adminFeedback").mockResolvedValue({
      success: true,
      data: [],
      meta: { page: 1, pageSize: 20, total: 0 },
    });
  });

  it("shows anonymous reader feedback to the guide administrator", async () => {
    vi.spyOn(guideApi, "adminFeedback").mockResolvedValue({
      success: true,
      data: [
        {
          id: "feedback-1",
          articleId: article.id,
          helpful: false,
          comment: "Cần chỉ rõ bước tiếp theo.",
          createdAt: "2026-10-19T00:00:00Z",
        },
      ],
      meta: { page: 1, pageSize: 20, total: 1 },
    });
    renderWorkspace();
    fireEvent.click(
      await screen.findByRole("button", {
        name: /Tìm và xem đề cử đã công bố/,
      }),
    );
    expect(await screen.findByText("Cần chỉ rõ bước tiếp theo.")).toBeDefined();
    expect(screen.getByText("Phản hồi từ người đọc (1)")).toBeDefined();
  });

  it("creates a draft article and reloads the management list", async () => {
    vi.spyOn(guideApi, "create").mockResolvedValue(article);
    renderWorkspace();

    expect(
      await screen.findByText("Tìm và xem đề cử đã công bố"),
    ).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Bài viết mới" }));
    fireEvent.change(screen.getByLabelText("Tiêu đề"), {
      target: { value: "Hướng dẫn mới" },
    });
    fireEvent.change(screen.getByLabelText("Đường dẫn"), {
      target: { value: "huong-dan-moi" },
    });
    fireEvent.change(screen.getByLabelText("Tóm tắt"), {
      target: { value: "Tóm tắt bài viết mới." },
    });
    fireEvent.change(screen.getByLabelText("Nội dung HTML"), {
      target: { value: "<h2>Bước đầu</h2><p>Nội dung.</p>" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu bản nháp" }));

    await waitFor(() =>
      expect(guideApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Hướng dẫn mới",
          slug: "huong-dan-moi",
          audiences: ["PUBLIC"],
        }),
      ),
    );
  });

  it("shows draft HTML as escaped text in the safe preview", async () => {
    renderWorkspace();
    await screen.findByText("Tìm và xem đề cử đã công bố");
    fireEvent.click(screen.getByRole("button", { name: "Bài viết mới" }));
    fireEvent.change(screen.getByLabelText("Nội dung HTML"), {
      target: { value: "<script>alert(1)</script><p>An toàn</p>" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Xem trước an toàn" }));

    expect(document.querySelector("pre")?.textContent).toBe(
      "<script>alert(1)</script><p>An toàn</p>",
    );
    expect(document.querySelector("script")).toBeNull();
  });

  it("publishes, archives, then removes a non-published article", async () => {
    const published = { ...article, status: "PUBLISHED" as const };
    const archived = { ...article, status: "ARCHIVED" as const };
    const setStatus = vi
      .spyOn(guideApi, "setStatus")
      .mockResolvedValueOnce(published)
      .mockResolvedValueOnce(archived);
    const remove = vi.spyOn(guideApi, "delete").mockResolvedValue(true);
    renderWorkspace();

    fireEvent.click(
      await screen.findByRole("button", { name: /Tìm và xem đề cử/ }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Xuất bản" }));
    await waitFor(() =>
      expect(setStatus).toHaveBeenCalledWith("guide-1", "PUBLISHED"),
    );
    fireEvent.click(screen.getByRole("button", { name: "Lưu trữ" }));
    await waitFor(() =>
      expect(setStatus).toHaveBeenCalledWith("guide-1", "ARCHIVED"),
    );
    fireEvent.click(screen.getByRole("button", { name: "Xóa bài viết" }));
    expect(screen.getByRole("alertdialog")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Xóa bài" }));
    await waitFor(() => expect(remove).toHaveBeenCalledWith("guide-1"));
  });
});
