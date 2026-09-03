import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PublicMap } from "@/components/public/public-map";

const mapMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  publicApi: { map: mapMock },
}));

describe("PublicMap", () => {
  it("keeps an accessible linked list alternative for map markers", async () => {
    mapMock.mockResolvedValue([
      {
        slug: "bo-nhan-dien-tmi",
        title: "Bộ nhận diện TMI",
        categoryName: "Thương hiệu",
        latitude: 10.7769,
        longitude: 106.7009,
      },
    ]);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { container } = render(
      <QueryClientProvider client={client}>
        <PublicMap category="BRAND" />
      </QueryClientProvider>,
    );

    await screen.findByText("Thương hiệu");
    const links = container.querySelectorAll(
      'a[href="/works/bo-nhan-dien-tmi"]',
    );
    expect(links).toHaveLength(2);
    expect(mapMock).toHaveBeenCalledWith("BRAND");
  });

  it("shows a clear empty state when no published work has coordinates", async () => {
    mapMock.mockResolvedValue([]);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <PublicMap />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText(/chưa có nội dung công khai kèm vị trí/i),
    ).toBeDefined();
  });

  it("shows an actionable error instead of leaving the loading indicator", async () => {
    const user = userEvent.setup();
    mapMock
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce([]);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <PublicMap />
      </QueryClientProvider>,
    );

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Chưa thể tải bản đồ đề cử",
    );
    await user.click(screen.getByRole("button", { name: "Thử lại" }));
    expect(
      await screen.findByText(/chưa có nội dung công khai kèm vị trí/i),
    ).toBeDefined();
  });
});
