import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ActivityHistory } from "@/components/engagement/activity-history";

const listMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/client", () => ({
  activityApi: { list: listMock },
}));

describe("ActivityHistory", () => {
  it("renders private favorite/share activity and cursor pagination", async () => {
    listMock.mockResolvedValueOnce({
      items: [
        {
          activityId: "activity-1",
          kind: "FAVORITE",
          publicWorkId: "work-1",
          slug: "public-work",
          title: "Public work",
          shortDescription: "A public work.",
          channel: null,
          createdAt: "2026-08-04T10:00:00Z",
        },
      ],
      nextCursor: "cursor-2",
    });

    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ActivityHistory />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Public work")).toBeDefined();
    expect(screen.getByText("Đã yêu thích")).toBeDefined();
    expect(
      screen.getByRole("button", { name: "Tải thêm hoạt động" }),
    ).toBeDefined();
    expect(listMock).toHaveBeenCalledWith(undefined);
  });
});
