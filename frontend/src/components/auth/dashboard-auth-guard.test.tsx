import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardAuthGuard } from "@/components/auth/dashboard-auth-guard";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/reviews/assignment-1",
  useRouter: () => ({ replace }),
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
  beforeEach(() => {
    replace.mockReset();
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
});
