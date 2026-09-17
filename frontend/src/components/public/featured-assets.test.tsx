import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { type ReactNode, createElement } from "react";
import { expect, it, vi } from "vitest";

import { FeaturedAssets } from "@/components/public/featured-assets";
import { publicApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({ publicApi: { works: vi.fn() } }));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) =>
    createElement("a", { href }, children),
}));

it("shows the newest published works on the home page", async () => {
  vi.mocked(publicApi.works).mockResolvedValue({
    success: true,
    data: [
      {
        id: "work-id",
        slug: "published-work",
        title: "Tác phẩm vừa công bố",
        shortDescription: "Nội dung công khai mới nhất.",
        authorDisplayName: "CNS",
        categoryName: "Tài sản trí tuệ số",
        categorySlug: "tai-san-tri-tue-so",
        tags: [],
        publishedAt: "2026-09-17T00:00:00Z",
        isFeatured: false,
        thumbnailUrl: "https://cdn.example.test/public/published-work.webp",
        thumbnailAltText: "Ảnh bìa tác phẩm vừa công bố",
      },
    ],
    meta: { page: 1, pageSize: 3, total: 1 },
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <FeaturedAssets />
    </QueryClientProvider>,
  );

  expect(await screen.findByText("Tác phẩm vừa công bố")).toBeTruthy();
  await waitFor(() =>
    expect(publicApi.works).toHaveBeenCalledWith({ page: 1, pageSize: 3 }),
  );
  expect(screen.getByAltText("Ảnh bìa tác phẩm vừa công bố")).toBeTruthy();
  expect(
    screen
      .getByRole("link", { name: /Tác phẩm vừa công bố/ })
      .getAttribute("href"),
  ).toBe("/works/published-work");
});
