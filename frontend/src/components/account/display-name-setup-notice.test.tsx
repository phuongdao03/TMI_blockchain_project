import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DisplayNameSetupNotice } from "@/components/account/display-name-setup-notice";

const api = vi.hoisted(() => ({ get: vi.fn() }));
const location = vi.hoisted(() => ({ path: "/workspace" }));
vi.mock("next/navigation", () => ({ usePathname: () => location.path }));
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
  sessionStorage.clear();
  location.path = "/workspace";
  auth.user = { id: "member-1" };
});

describe("DisplayNameSetupNotice", () => {
  it.each(["/", "/dossiers/new", "/account"])(
    "does not interrupt %s",
    (path) => {
      location.path = path;
      render(<DisplayNameSetupNotice />, { wrapper });
      expect(api.get).not.toHaveBeenCalled();
      expect(screen.queryByRole("note")).toBeNull();
    },
  );

  it("lets the member defer the reminder for this session", async () => {
    api.get.mockResolvedValue({ displayName: null });
    render(<DisplayNameSetupNotice />, { wrapper });
    fireEvent.click(await screen.findByRole("button", { name: "Để sau" }));
    expect(screen.queryByRole("note")).toBeNull();
    expect(sessionStorage.getItem("display-name-reminder:member-1")).toBe(
      "later",
    );
  });
  it("asks an authenticated member without a display name to set one", async () => {
    api.get.mockResolvedValue({ displayName: null });
    render(<DisplayNameSetupNotice />, { wrapper });

    const status = await screen.findByRole("note");
    expect(status.tagName).toBe("ASIDE");
    expect(
      screen.getByRole("link", { name: "Thêm tên" }).getAttribute("href"),
    ).toBe("/account#display-name");
  });

  it("does not show after the member has set a display name", async () => {
    api.get.mockResolvedValue({ displayName: "Lan Anh" });
    render(<DisplayNameSetupNotice />, { wrapper });

    await vi.waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("note")).toBeNull();
  });
});
