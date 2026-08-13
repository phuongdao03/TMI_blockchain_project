import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LogoutButton } from "@/components/auth/logout-button";

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  refresh: vi.fn(),
  signOut: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace, refresh: mocks.refresh }),
}));

vi.mock("@/lib/firebase/client", () => ({
  getFirebaseAuth: () => ({ name: "firebase-auth" }),
}));

vi.mock("firebase/auth", () => ({ signOut: mocks.signOut }));

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

describe("LogoutButton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Object.values(mocks).forEach((mock) => mock.mockReset());
    document.cookie = "tmi_csrf=e2e-csrf; Path=/";
  });

  it("revokes the backend session, signs out Firebase and returns to login", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, {
        status: 204,
        headers: { "X-Request-Id": "logout-1" },
      }),
    );
    mocks.signOut.mockResolvedValue(undefined);
    render(<LogoutButton />, { wrapper: Wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));

    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/login"));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/logout",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: expect.any(Headers),
      }),
    );
    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get("X-CSRF-Token")).toBe("e2e-csrf");
    expect(mocks.signOut).toHaveBeenCalledWith({ name: "firebase-auth" });
    expect(mocks.refresh).toHaveBeenCalledOnce();
  });

  it("shows a safe error without exposing backend details", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: false,
          error: {
            code: "SESSION_TOKEN_REJECTED",
            message: "refresh-token-secret-value",
            details: {},
            request_id: "logout-2",
          },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<LogoutButton />, { wrapper: Wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));

    expect((await screen.findByRole("alert")).textContent).toBe(
      "Không thể đăng xuất lúc này. Vui lòng thử lại.",
    );
    expect(
      screen.queryByText(/refresh-token-secret-value|SESSION_TOKEN_REJECTED/),
    ).toBeNull();
    expect(mocks.replace).not.toHaveBeenCalled();
  });
});
