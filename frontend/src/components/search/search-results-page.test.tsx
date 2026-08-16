import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SearchResultsPage } from "@/components/search/search-results-page";
import { publicApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  publicApi: {
    search: vi.fn(),
    searchFacets: vi.fn(),
  },
}));

vi.mock("@/components/search/search-autocomplete", () => ({
  SearchAutocomplete: ({
    defaultValue,
    name,
  }: {
    defaultValue?: string;
    name?: string;
  }) => (
    <input aria-label="Tìm tác phẩm" defaultValue={defaultValue} name={name} />
  ),
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.mocked(publicApi.search).mockResolvedValue({
    success: true,
    data: [
      {
        id: "25324c61-89fd-44c2-b803-67d8cf5f203e",
        slug: "son-mai-di-san",
        title: "Sơn mài <img src=x onerror=alert(1)>",
        shortDescription: "Hồ sơ công khai đã được xác lập.",
        authorDisplayName: "Nguyễn An",
        categoryName: "Mỹ thuật",
        categorySlug: "my-thuat",
        certificateNumber: "TMI-2026-001",
        certificateStatus: "ACTIVE",
        publishedAt: "2026-08-01T00:00:00Z",
      },
    ],
    meta: {
      requestId: "request-search",
      nextCursor: "next-safe-cursor",
      durationMs: 12,
      version: "search-v1",
    },
  });
  vi.mocked(publicApi.searchFacets).mockResolvedValue({
    categories: [{ slug: "my-thuat", label: "Mỹ thuật", count: 7 }],
    tags: [{ slug: "di-san", label: "Di sản", count: 4 }],
    approximate: false,
  });
});

afterEach(() => vi.clearAllMocks());

describe("SearchResultsPage", () => {
  it("uses compact workspace copy without a redundant back link", () => {
    render(
      <SearchResultsPage
        embedded
        parameters={{ tags: [], tagsMode: "any", sort: "newest" }}
      />,
      { wrapper },
    );

    expect(
      screen.getByRole("heading", { name: "Tìm nội dung bạn quan tâm" }),
    ).toBeDefined();
    expect(
      screen.queryByRole("link", { name: /Quay lại thư viện/ }),
    ).toBeNull();
    expect(screen.queryByText("TMI Search Index")).toBeNull();
  });

  it("keeps query state in links and renders backend text without raw HTML", async () => {
    render(
      <SearchResultsPage
        parameters={{
          q: "sơn mài",
          category: "my-thuat",
          tags: [],
          tagsMode: "any",
          sort: "relevance",
        }}
      />,
      { wrapper },
    );

    expect(await screen.findByText(/Sơn mài <img/)).toBeTruthy();
    expect(document.querySelector("img")).toBeNull();
    await waitFor(() => expect(publicApi.search).toHaveBeenCalledTimes(1));
    expect(publicApi.search).toHaveBeenCalledWith(
      expect.objectContaining({ category: "my-thuat", q: "sơn mài" }),
      expect.any(AbortSignal),
    );

    const clearCategory = screen.getByRole("link", {
      name: /Bỏ danh mục Mỹ thuật/,
    });
    expect(clearCategory.getAttribute("href")).toContain("q=s%C6%A1n+m%C3%A0i");
    expect(clearCategory.getAttribute("href")).not.toContain("category=");
    const next = screen.getByRole("link", { name: "Trang tiếp" });
    expect(next.getAttribute("href")).toContain("cursor=next-safe-cursor");
  });

  it("moves focus into the mobile drawer and closes it with Escape", async () => {
    const user = userEvent.setup();
    render(
      <SearchResultsPage
        parameters={{ tags: [], tagsMode: "any", sort: "newest" }}
      />,
      { wrapper },
    );

    await user.click(screen.getByRole("button", { name: /Bộ lọc/ }));
    const close = screen.getByRole("button", { name: "Đóng bộ lọc" });
    await waitFor(() => expect(document.activeElement).toBe(close));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders actionable empty and retry states without losing URL state", async () => {
    vi.mocked(publicApi.search)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({
        success: true,
        data: [],
        meta: {
          requestId: "request-empty",
          nextCursor: null,
          durationMs: 8,
          version: "search-v1",
        },
      });
    const user = userEvent.setup();
    render(
      <SearchResultsPage
        parameters={{
          q: "di sản",
          tags: [],
          tagsMode: "any",
          sort: "relevance",
        }}
      />,
      { wrapper },
    );

    await user.click(await screen.findByRole("button", { name: "Thử lại" }));
    expect(
      await screen.findByText("Chưa có kết quả công khai phù hợp"),
    ).toBeTruthy();
    expect(
      screen.getByRole("textbox", { name: "Tìm tác phẩm" }),
    ).toHaveProperty("value", "di sản");
  });
});
