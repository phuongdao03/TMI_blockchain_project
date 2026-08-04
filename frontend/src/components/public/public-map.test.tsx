import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
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
      'a[href="/tai-san/bo-nhan-dien-tmi"]',
    );
    expect(links).toHaveLength(2);
    expect(mapMock).toHaveBeenCalledWith("BRAND");
  });
});
