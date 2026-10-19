import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: routerPush }) }));

import AccountGuidePage from "@/app/(dashboard)/help/page";
import { guideApi } from "@/lib/api/client";
import { AuthUserProvider } from "@/lib/auth/user-context";

function renderFor(roles: string[], isEmployee = false) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  vi.spyOn(guideApi, "accessibleList").mockResolvedValue({
    success: true,
    data: [],
    meta: { page: 1, pageSize: 24, total: 0 },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthUserProvider
        user={{
          id: "account-1",
          email: "test@example.vn",
          roles,
          isEmployee,
          accountType: null,
        }}
      >
        <AccountGuidePage />
      </AuthUserProvider>
    </QueryClientProvider>,
  );
}

describe("account help page", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("requests guides for the current role and linked employee status", async () => {
    renderFor(["USER"], true);
    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Hướng dẫn sử dụng",
      }),
    ).toBeDefined();
    expect(screen.queryByText(/Vai trò:/)).toBeNull();
    expect(guideApi.accessibleList).toHaveBeenCalled();
  });
});
