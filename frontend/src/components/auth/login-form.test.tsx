import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/components/auth/login-form";

const replace = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh }),
}));

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

describe("LoginForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    replace.mockReset();
    refresh.mockReset();
  });

  it("shows accessible field errors before making a request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<LoginForm />, { wrapper: Wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    expect(await screen.findByText("Vui lòng nhập email.")).toBeDefined();
    expect(screen.getByText("Vui lòng nhập mật khẩu.")).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("submits the API contract and redirects after success", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: {
            user: {
              id: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
              email: "owner@tmigroup.vn",
              roles: ["APPLICANT"],
            },
          },
          meta: { request_id: "request-1" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<LoginForm next="/dashboard" />, { wrapper: Wrapper });

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@tmigroup.vn",
    );
    await userEvent.type(
      screen.getByLabelText("Mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(refresh).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/auth/login");
    expect(init?.credentials).toBe("include");
    expect(JSON.parse(String(init?.body))).toEqual({
      email: "owner@tmigroup.vn",
      password: "correct horse battery staple",
      deviceName: "Trình duyệt web",
    });
  });
});
