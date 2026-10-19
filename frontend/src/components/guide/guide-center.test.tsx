import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: routerPush }) }));

import {
  GuideCenter,
  guideCategoryLabel,
} from "@/components/guide/guide-center";
import { AuthUserProvider } from "@/lib/auth/user-context";
import { guideApi } from "@/lib/api/client";
import type { CmsGuideArticle } from "@/lib/api/types";

const article: CmsGuideArticle = {
  id: "guide-1",
  title: "Tìm và xem đề cử đã công bố",
  slug: "explore-nominations",
  summary: "Mở thư viện để tìm nội dung công khai.",
  category: "getting-started",
  audiences: ["PUBLIC"],
  bodyHtml: "<h2>Mở thư viện</h2><p>Chọn nội dung.</p>",
  status: "PUBLISHED",
  sortOrder: 10,
  version: 1,
  readingMinutes: 1,
  publishedAt: "2026-10-18T00:00:00Z",
  createdAt: "2026-10-18T00:00:00Z",
  updatedAt: "2026-10-18T00:00:00Z",
};

function renderCenter(scope: "public" | "account" = "public") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const center = <GuideCenter scope={scope} />;
  return render(
    <QueryClientProvider client={client}>
      {scope === "account" ? (
        <AuthUserProvider
          user={{
            id: "user-1",
            email: "person@example.vn",
            roles: ["USER"],
            isEmployee: true,
            accountType: null,
          }}
        >
          {center}
        </AuthUserProvider>
      ) : (
        center
      )}
    </QueryClientProvider>,
  );
}

describe("GuideCenter", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("uses readable labels for seeded legacy categories", () => {
    expect(guideCategoryLabel("certificates")).toBe("Bằng xác lập");
    expect(guideCategoryLabel("reviews")).toBe("Thẩm định");
    expect(guideCategoryLabel("faq")).toBe("Câu hỏi thường gặp");
  });

  it("lists public guides and links to the public reader", async () => {
    vi.spyOn(guideApi, "publicList").mockResolvedValue({
      success: true,
      data: [article],
      meta: { request_id: "request-1", page: 1, pageSize: 24, total: 1 },
    });
    renderCenter();

    expect(
      (await screen.findAllByRole("link", { name: /Tìm và xem đề cử/ })).some(
        (link) => link.getAttribute("href") === "/guide/explore-nominations",
      ),
    ).toBe(true);
    expect(guideApi.publicList).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, pageSize: 24 }),
    );
  });

  it("requests role and employee scoped guides for signed in users", async () => {
    const publicList = vi.spyOn(guideApi, "publicList");
    vi.spyOn(guideApi, "accessibleList").mockResolvedValue({
      success: true,
      data: [article],
      meta: { request_id: "request-2", page: 1, pageSize: 24, total: 1 },
    });
    renderCenter("account");

    expect(
      (await screen.findAllByRole("link", { name: /Tìm và xem đề cử/ })).some(
        (link) => link.getAttribute("href") === "/help/explore-nominations",
      ),
    ).toBe(true);
    expect(guideApi.accessibleList).toHaveBeenCalled();
    expect(publicList).not.toHaveBeenCalled();
    expect(
      screen.getByRole("heading", { level: 1, name: "Hướng dẫn sử dụng" }),
    ).toBeDefined();
    expect(screen.queryByText(/Vai trò:/)).toBeNull();
  });

  it("derives topics and FAQs from accessible articles only", async () => {
    const dossierGuide: CmsGuideArticle = {
      ...article,
      id: "guide-dossier",
      title: "Tạo và gửi hồ sơ đề cử",
      slug: "create-and-submit-a-dossier",
      category: "dossiers",
      audiences: ["USER"],
    };
    const faqGuide: CmsGuideArticle = {
      ...article,
      id: "guide-faq",
      title: "Câu hỏi thường gặp",
      slug: "common-account-and-guide-questions",
      category: "faq",
      bodyHtml:
        "<h2>Câu hỏi thường gặp</h2><h3>Tôi bắt đầu từ đâu?</h3><p>Mở thư viện đề cử.</p>",
    };
    vi.spyOn(guideApi, "accessibleList").mockResolvedValue({
      success: true,
      data: [dossierGuide, faqGuide],
      meta: { request_id: "request-4", page: 1, pageSize: 100, total: 2 },
    });
    renderCenter("account");

    expect(
      await screen.findByRole("option", { name: "Hồ sơ đề cử" }),
    ).toBeDefined();
    expect(
      screen.getByRole("option", { name: "Câu hỏi thường gặp" }),
    ).toBeDefined();
    expect(screen.queryByRole("option", { name: "Quản trị" })).toBeNull();
    expect(screen.queryByRole("option", { name: "Nhân sự" })).toBeNull();
    expect(
      screen.getByRole("link", { name: /Tạo và gửi hồ sơ đề cử/ }),
    ).toBeDefined();
    expect(screen.queryByText(/Vai trò: USER/)).toBeNull();
    expect(screen.queryByText("Ctrl K")).toBeNull();
  });

  it("does not show unrelated guides when a search has no matches", async () => {
    vi.spyOn(guideApi, "publicList").mockImplementation(
      async (filters = {}) => ({
        success: true,
        data: filters.query ? [] : [article],
        meta: {
          request_id: "request-5",
          page: 1,
          pageSize: 24,
          total: filters.query ? 0 : 1,
        },
      }),
    );
    renderCenter();
    fireEvent.change(screen.getByLabelText("Tìm trong hướng dẫn"), {
      target: { value: "Nạp tiền" },
    });

    expect(await screen.findByText(/Không tìm thấy hướng dẫn/)).toBeDefined();
    expect(screen.queryByRole("link", { name: /Tìm và xem đề cử/ })).toBeNull();
  });

  it("moves the keyboard shortcut to the compact inline search", async () => {
    vi.spyOn(guideApi, "publicList").mockResolvedValue({
      success: true,
      data: [article],
      meta: { request_id: "request-3", page: 1, pageSize: 24, total: 1 },
    });
    renderCenter();

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(screen.getByLabelText("Tìm trong hướng dẫn").matches(":focus")).toBe(
      true,
    );
    await waitFor(() => expect(guideApi.publicList).toHaveBeenCalled());
  });
});
