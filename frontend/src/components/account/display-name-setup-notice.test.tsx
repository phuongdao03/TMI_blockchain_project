import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DisplayNameSetupNotice } from "@/components/account/display-name-setup-notice";

const api = vi.hoisted(() => ({ get: vi.fn() }));
const auth = vi.hoisted(() => ({ user: null as null | { id: string } }));
vi.mock("@/lib/api/client", () => ({ profileApi: api }));
vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => auth.user }));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  auth.user = { id: "member-1" };
});

describe("DisplayNameSetupNotice", () => {
  it("asks an authenticated member without a display name to set one", async () => {
    api.get.mockResolvedValue({ displayName: null });
    render(<DisplayNameSetupNotice />, { wrapper });

    const status = await screen.findByRole("status");
    expect(status.tagName).toBe("DIV");
    expect(
      screen.getByRole("link", { name: "Thiết lập" }).getAttribute("href"),
    ).toBe("/account");
  });

  it("does not show after the member has set a display name", async () => {
    api.get.mockResolvedValue({ displayName: "Lan Anh" });
    render(<DisplayNameSetupNotice />, { wrapper });

    await vi.waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("status")).toBeNull();
  });
});
