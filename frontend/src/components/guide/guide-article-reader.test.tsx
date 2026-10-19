import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GuideArticleReader } from "@/components/guide/guide-article-reader";
import { guideApi } from "@/lib/api/client";
import type { CmsGuideArticle } from "@/lib/api/types";

const article: CmsGuideArticle = {
  id: "guide-1",
  title: "Tìm và xem đề cử đã công bố",
  slug: "explore-nominations",
  summary: "Mở thư viện, tìm nội dung đã công bố và xem thông tin.",
  category: "getting-started",
  audiences: ["PUBLIC"],
  bodyHtml: '<h2>Mở thư viện</h2><p>Chọn <a href="/works">thư viện</a>.</p>',
  status: "PUBLISHED",
  sortOrder: 10,
  version: 1,
  readingMinutes: 1,
  publishedAt: "2026-10-18T00:00:00Z",
  createdAt: "2026-10-18T00:00:00Z",
  updatedAt: "2026-10-18T00:00:00Z",
};

function renderReader(scope: "public" | "account" = "public") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>
      <GuideArticleReader scope={scope} slug={article.slug} />
    </QueryClientProvider>,
  );
}

describe("GuideArticleReader", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.removeItem("guide-feedback-token");
    window.localStorage.removeItem(`guide-feedback:${article.slug}`);
    vi.spyOn(guideApi, "publicArticle").mockResolvedValue(article);
    vi.spyOn(guideApi, "publicList").mockResolvedValue({
      success: true,
      data: [article],
      meta: { page: 1, pageSize: 100, total: 1 },
    });
  });

  it("renders a linked contents list and sanitized article body", async () => {
    renderReader();
    expect(
      await screen.findByRole("heading", { level: 1, name: article.title }),
    ).toBeDefined();
    expect(screen.getByRole("heading", { name: "Mở thư viện" })).toBeDefined();
    expect(document.querySelector("h2#mo-thu-vien")).not.toBeNull();
    expect(document.querySelector('a[href="/works"]')).not.toBeNull();
  });

  it.each([
    ["public", "/guide"],
    ["account", "/help"],
  ] as const)(
    "shows a clear return link for %s guides",
    async (scope, href) => {
      if (scope === "account") {
        vi.spyOn(guideApi, "accessibleArticle").mockResolvedValue(article);
        vi.spyOn(guideApi, "accessibleList").mockResolvedValue({
          success: true,
          data: [article],
          meta: { page: 1, pageSize: 100, total: 1 },
        });
      }
      renderReader(scope);
      await screen.findByRole("heading", { level: 1, name: article.title });
      const returnLinks = screen.getAllByRole("link", {
        name: "Quay lại danh sách hướng dẫn",
      });
      expect(returnLinks.length).toBe(2);
      expect(
        returnLinks.every((link) => link.getAttribute("href") === href),
      ).toBe(true);
    },
  );

  it("shows breadcrumbs, linked contents and adjacent articles", async () => {
    vi.spyOn(guideApi, "publicArticle").mockResolvedValue({
      ...article,
      bodyHtml: `${article.bodyHtml}<h2>Kiểm tra kết quả</h2><p>Đã mở thư viện.</p>`,
    });
    const sibling: CmsGuideArticle = {
      ...article,
      id: "guide-sibling",
      title: "Tạo tài khoản và đăng nhập an toàn",
      slug: "create-account-and-sign-in",
      category: article.category,
      sortOrder: 20,
    };
    vi.spyOn(guideApi, "publicList").mockResolvedValue({
      success: true,
      data: [article, sibling],
      meta: { page: 1, pageSize: 100, total: 2 },
    });
    renderReader();

    await screen.findByRole("heading", { level: 1, name: article.title });
    expect(screen.getByRole("navigation", { name: "Đường dẫn" })).toBeDefined();
    expect(
      screen
        .getAllByRole("link", { name: "Mở thư viện" })
        .some((link) => link.getAttribute("href") === "#mo-thu-vien"),
    ).toBe(true);
    expect(
      screen.getByRole("navigation", { name: "Chuyển bài" }),
    ).toBeDefined();
  });

  it("submits anonymous feedback for a public article", async () => {
    const submit = vi
      .spyOn(guideApi, "submitFeedback")
      .mockResolvedValue({ accepted: true });
    renderReader();
    await screen.findByRole("heading", { level: 1, name: article.title });
    fireEvent.click(screen.getByRole("button", { name: "Có, hữu ích" }));
    fireEvent.change(screen.getByLabelText(/Góp ý thêm/), {
      target: { value: "Các bước rất rõ." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Gửi phản hồi" }));

    await waitFor(() => expect(submit).toHaveBeenCalled());
    expect(submit).toHaveBeenCalledWith(
      article.slug,
      expect.objectContaining({ helpful: true, comment: "Các bước rất rõ." }),
    );
    expect(
      await screen.findByText("Cảm ơn bạn đã gửi phản hồi."),
    ).toBeDefined();
  });
});
