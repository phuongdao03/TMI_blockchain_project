import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: routerPush }) }));

import UserGuidePage from "@/app/(public)/guide/page";
import { guideApi } from "@/lib/api/client";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  vi.spyOn(guideApi, "publicList").mockResolvedValue({
    success: true,
    data: [],
    meta: { page: 1, pageSize: 24, total: 0 },
  });
  return render(
    <QueryClientProvider client={client}>
      <UserGuidePage />
    </QueryClientProvider>,
  );
}

describe("public guide page", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("provides public documentation browsing and an empty state", async () => {
    renderPage();
    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Hướng dẫn sử dụng",
      }),
    ).toBeDefined();
    expect(screen.getByLabelText("Tìm trong hướng dẫn")).toBeDefined();
    expect(await screen.findByText("Không tìm thấy hướng dẫn")).toBeDefined();
  });
});
