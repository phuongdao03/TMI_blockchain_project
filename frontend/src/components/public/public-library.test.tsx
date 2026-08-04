import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { createElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PublicLibrary } from "@/components/public/public-library";
import { PublicWorkCard } from "@/components/public/public-work-card";
import { publicApi } from "@/lib/api/client";
import type { PublicCatalogWork } from "@/lib/api/types";

vi.mock("@/lib/api/client", () => ({
  publicApi: {
    autocomplete: vi.fn(),
    categories: vi.fn(),
    featuredWorks: vi.fn(),
    tags: vi.fn(),
    works: vi.fn(),
  },
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

vi.mock("next/image", () => ({
  default: (props: Record<string, unknown>) => {
    const imageProps = { ...props };
    delete imageProps.fill;
    delete imageProps.unoptimized;
    return createElement("img", imageProps);
  },
}));

const work: PublicCatalogWork = {
  id: "25324c61-89fd-44c2-b803-67d8cf5f203e",
  slug: "di-san-so",
  title: "Di sản số",
  shortDescription: "Mô tả công khai đã được biên tập an toàn.",
  authorDisplayName: "TMI Studio",
  categoryName: "Nghệ thuật số",
  categorySlug: "nghe-thuat-so",
  tags: [{ name: "Đương đại", slug: "duong-dai" }],
  publishedAt: "2026-07-31T10:00:00Z",
  isFeatured: false,
  thumbnailUrl: "https://cdn.example.test/public/work.webp",
  thumbnailAltText: "Tác phẩm nghệ thuật số",
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.mocked(publicApi.autocomplete).mockResolvedValue([]);
  vi.mocked(publicApi.works).mockResolvedValue({
    success: true,
    data: [work],
    meta: { page: 2, pageSize: 12, total: 13 },
  });
  vi.mocked(publicApi.featuredWorks).mockResolvedValue([work]);
  vi.mocked(publicApi.categories).mockResolvedValue([
    {
      id: "e02bb168-d32a-4ce5-8e2a-bfeef3788bb3",
      code: "DIGITAL_ART",
      name: "Nghệ thuật số",
      slug: "nghe-thuat-so",
      description: null,
      assetCount: 1,
    },
  ]);
  vi.mocked(publicApi.tags).mockResolvedValue([
    {
      id: "44ecb5a4-41b5-4c99-892b-8c0757af1c68",
      name: "Đương đại",
      slug: "duong-dai",
      isActive: true,
    },
  ]);
});

afterEach(() => vi.clearAllMocks());

describe("PublicLibrary", () => {
  it("hydrates deep-link filters and requests the exact API contract", async () => {
    render(
      <PublicLibrary
        category="nghe-thuat-so"
        page={2}
        publishedFrom="2026-01-01"
        query="di sản"
        sort="popular"
        tag="duong-dai"
      />,
      { wrapper },
    );

    expect(await screen.findByText("Di sản số")).toBeTruthy();
    await waitFor(() =>
      expect(publicApi.works).toHaveBeenCalledWith(
        expect.objectContaining({
          category: "nghe-thuat-so",
          page: 2,
          publishedFrom: "2026-01-01",
          query: "di sản",
          sort: "popular",
          tag: "duong-dai",
        }),
      ),
    );
    expect(
      (screen.getByLabelText("Tìm tác phẩm") as HTMLInputElement).value,
    ).toBe("di sản");
    await waitFor(() =>
      expect(
        (screen.getByLabelText("Danh mục") as HTMLSelectElement).value,
      ).toBe("nghe-thuat-so"),
    );
    const previousHref = screen
      .getByRole("link", { name: /Trang trước/ })
      .getAttribute("href");
    expect(previousHref).toContain("category=nghe-thuat-so");
    expect(previousHref).not.toContain("page=");
  });

  it("renders an actionable empty state", async () => {
    vi.mocked(publicApi.works).mockResolvedValueOnce({
      success: true,
      data: [],
      meta: { page: 1, pageSize: 12, total: 0 },
    });
    render(<PublicLibrary page={1} query="không tồn tại" sort="newest" />, {
      wrapper,
    });
    expect(
      await screen.findByText("Chưa tìm thấy tác phẩm phù hợp"),
    ).toBeTruthy();
    expect(
      screen.getByRole("link", { name: "Xóa bộ lọc" }).getAttribute("href"),
    ).toBe("/thu-vien");
  });

  it("retries an API error without losing filters", async () => {
    vi.mocked(publicApi.works)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({
        success: true,
        data: [work],
        meta: { page: 1, pageSize: 12, total: 1 },
      });
    const user = userEvent.setup();
    render(<PublicLibrary page={1} query="di sản" sort="newest" />, {
      wrapper,
    });
    await user.click(await screen.findByRole("button", { name: "Thử lại" }));
    expect(await screen.findByText("Di sản số")).toBeTruthy();
    expect(publicApi.works).toHaveBeenCalledTimes(2);
  });

  it("moves keyboard focus into the mobile filter and closes on Escape", async () => {
    const user = userEvent.setup();
    render(<PublicLibrary page={1} query="di sản" sort="newest" />, {
      wrapper,
    });
    await user.click(screen.getByRole("button", { name: /Bộ lọc/ }));
    const close = screen.getByRole("button", { name: "Đóng bộ lọc" });
    await waitFor(() => expect(document.activeElement).toBe(close));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("PublicWorkCard", () => {
  it("keeps a loading surface until the responsive image resolves", () => {
    render(<PublicWorkCard position={1} source="list" work={work} />);
    expect(screen.getByTestId("image-loading")).toBeTruthy();
    fireEvent.load(screen.getByAltText("Tác phẩm nghệ thuật số"));
    expect(screen.queryByTestId("image-loading")).toBeNull();
  });
});
