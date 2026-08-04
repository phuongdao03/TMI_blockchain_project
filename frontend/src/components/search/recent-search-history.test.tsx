import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RecentSearchHistory } from "@/components/search/recent-search-history";
import { searchHistoryApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  searchHistoryApi: {
    get: vi.fn(),
    setConsent: vi.fn(),
    record: vi.fn(),
    clear: vi.fn(),
  },
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(searchHistoryApi.get).mockResolvedValue({
    isEnabled: false,
    items: [],
  });
  vi.mocked(searchHistoryApi.setConsent).mockResolvedValue({
    isEnabled: true,
    items: [],
  });
  vi.mocked(searchHistoryApi.record).mockResolvedValue({ recorded: true });
  vi.mocked(searchHistoryApi.clear).mockResolvedValue(undefined);
});

describe("RecentSearchHistory", () => {
  it("requires explicit opt-in before recording a successful query", async () => {
    const user = userEvent.setup();
    render(<RecentSearchHistory currentQuery="Sơn mài" resultsReady />, {
      wrapper,
    });

    expect(await screen.findByText(/Lịch sử đang tắt/)).toBeTruthy();
    expect(searchHistoryApi.record).not.toHaveBeenCalled();

    await user.click(
      screen.getByRole("button", { name: "Bật lịch sử tìm kiếm" }),
    );
    await waitFor(() =>
      expect(searchHistoryApi.setConsent).toHaveBeenCalledWith(true),
    );
    await waitFor(() =>
      expect(searchHistoryApi.record).toHaveBeenCalledWith("Sơn mài"),
    );
  });

  it("renders recent suggestions and clears only the signed-in user's list", async () => {
    vi.mocked(searchHistoryApi.get).mockResolvedValue({
      isEnabled: true,
      items: [
        {
          id: "e9684789-ae9c-4a26-b937-ab9bfd41b71f",
          displayQuery: "Di sản số",
          searchedAt: "2026-08-01T00:00:00Z",
        },
      ],
    });
    const user = userEvent.setup();
    render(<RecentSearchHistory resultsReady={false} />, { wrapper });

    const suggestion = await screen.findByRole("link", { name: "Di sản số" });
    expect(suggestion.getAttribute("href")).toContain(
      "q=Di+s%E1%BA%A3n+s%E1%BB%91",
    );
    await user.click(screen.getByRole("button", { name: "Xóa lịch sử" }));
    await waitFor(() => expect(searchHistoryApi.clear).toHaveBeenCalledOnce());
  });

  it("announces consent failures without exposing query content", async () => {
    vi.mocked(searchHistoryApi.setConsent).mockRejectedValue(
      new Error("provider details must stay private"),
    );
    const user = userEvent.setup();
    render(<RecentSearchHistory resultsReady={false} />, { wrapper });

    await user.click(
      await screen.findByRole("button", { name: "Bật lịch sử tìm kiếm" }),
    );
    expect(
      await screen.findByText("Chưa thể cập nhật lịch sử. Vui lòng thử lại."),
    ).toBeTruthy();
    expect(screen.queryByText(/provider details/)).toBeNull();
  });
});
