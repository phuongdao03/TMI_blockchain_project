import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SearchAnalyticsDashboard } from "@/components/admin/search-analytics-dashboard";
import { searchAnalyticsApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  searchAnalyticsApi: { get: vi.fn(), exportUrl: vi.fn(() => "/export.csv") },
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.mocked(searchAnalyticsApi.get).mockResolvedValue({
    searchCount: 100,
    zeroResultCount: 8,
    clickCount: 32,
    clickThroughRate: 0.32,
    zeroResultRate: 0.08,
    latencyP95Ms: 184,
    privacyMode: "aggregate-only",
    points: [
      {
        periodStart: "2026-08-01T00:00:00Z",
        categorySlug: null,
        searchCount: 100,
        zeroResultCount: 8,
        clickCount: 32,
        latencyP95Ms: 184,
      },
    ],
  });
});

describe("SearchAnalyticsDashboard", () => {
  it("renders aggregate KPIs without raw queries or user identifiers", async () => {
    render(<SearchAnalyticsDashboard />, { wrapper });
    expect((await screen.findAllByText("100")).length).toBe(2);
    expect(screen.getByText("32%")).toBeTruthy();
    expect(screen.getAllByText("184 ms")).toHaveLength(2);
    expect(screen.getByText("AGGREGATE ONLY")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/email|userId|sessionId/i);
  });
});
