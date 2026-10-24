import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { AUTH_SESSION_CHANGE_KEY } from "@/lib/auth/session-sync";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardAuthGuard } from "@/components/auth/dashboard-auth-guard";

const replace = vi.fn();
const navigationState = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", () => ({
  usePathname: () => "/reviews/assignment-1",
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(navigationState.search),
}));

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false } },
        })
      }
    >
      {children}
    </QueryClientProvider>
  );
}

describe("DashboardAuthGuard", () => {
  it("hides protected content when another tab changes the session", async () => {
    render(
      <DashboardAuthGuard
        initialUser={{
          id: "owner",
          email: "owner@example.vn",
          roles: ["USER"],
          accountType: "INDIVIDUAL_APPLICANT",
        }}
      >
        <p>Protected wallet content</p>
      </DashboardAuthGuard>,
      { wrapper: Wrapper },
    );
    expect(screen.getByText("Protected wallet content")).toBeDefined();
    act(() =>
      window.dispatchEvent(
        new StorageEvent("storage", { key: AUTH_SESSION_CHANGE_KEY }),
      ),
    );
    await waitFor(() =>
      expect(screen.queryByText("Protected wallet content")).toBeNull(),
    );
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith(
        "/login?next=%2Freviews%2Fassignment-1",
      ),
    );
  });
  beforeEach(() => {
    replace.mockReset();
    navigationState.search = "";
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: false,
          error: { code: "AUTH_REQUIRED", message: "unauthorized" },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      ),
    );
  });

  it("preserves the protected destination when redirecting to login", async () => {
    render(
      <DashboardAuthGuard initialUser={null}>
        <div>protected</div>
      </DashboardAuthGuard>,
      { wrapper: Wrapper },
    );

    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith(
        "/login?next=%2Freviews%2Fassignment-1",
      ),
    );
  });

  it("preserves a protected destination query when redirecting to login", async () => {
    navigationState.search = "tab=history&page=3";
    render(
      <DashboardAuthGuard initialUser={null}>
        <div>protected</div>
      </DashboardAuthGuard>,
      { wrapper: Wrapper },
    );

    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith(
        "/login?next=%2Freviews%2Fassignment-1%3Ftab%3Dhistory%26page%3D3",
      ),
    );
  });
});
