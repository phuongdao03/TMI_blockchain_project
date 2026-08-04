import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RegisterForm } from "@/components/auth/register-form";

describe("RegisterForm", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("rejects mismatched passwords without a network request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<RegisterForm />);

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@tmigroup.vn",
    );
    await userEvent.type(
      screen.getByLabelText("Mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.type(
      screen.getByLabelText("Xác nhận mật khẩu"),
      "different horse battery value",
    );
    await userEvent.click(screen.getByRole("button", { name: "Đăng ký" }));

    expect(
      await screen.findByText("Mật khẩu xác nhận không khớp."),
    ).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows the same accepted state returned by the generic API", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: { message: "accepted" },
          meta: { request_id: "request-2" },
        }),
        { status: 202, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<RegisterForm />);

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@tmigroup.vn",
    );
    await userEvent.type(
      screen.getByLabelText("Mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.type(
      screen.getByLabelText("Xác nhận mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.click(screen.getByRole("button", { name: "Đăng ký" }));

    expect(await screen.findByRole("status")).toBeDefined();
    expect(screen.getByText(/hướng dẫn xác minh đã được gửi/i)).toBeDefined();
  });

  it("submits the selected organization applicant account type", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: { message: "accepted" },
          meta: { request_id: "request-3" },
        }),
        { status: 202, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<RegisterForm />);

    await userEvent.click(screen.getByRole("radio", { name: /Tổ chức/i }));
    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "organization@tmigroup.vn",
    );
    await userEvent.type(
      screen.getByLabelText("Mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.type(
      screen.getByLabelText("Xác nhận mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.click(screen.getByRole("button", { name: "Đăng ký" }));

    expect(fetchMock).toHaveBeenCalledOnce();
    const options = fetchMock.mock.calls[0]?.[1];
    expect(JSON.parse(String(options?.body))).toMatchObject({
      accountType: "ORGANIZATION_APPLICANT",
    });
  });

  it("offers a browse-only account intent without dossier privileges", () => {
    render(<RegisterForm />);

    expect(
      screen.getByRole("radio", { name: /Khám phá công khai/i }),
    ).toBeDefined();
  });

  it("starts Google OAuth with the selected account intent and shows provider errors", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: false,
          error: {
            code: "OAUTH_PROVIDER_UNAVAILABLE",
            message: "provider unavailable",
            details: {},
            request_id: "request-google-1",
          },
        }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<RegisterForm />);

    await userEvent.click(
      screen.getByRole("button", { name: "Tiếp tục với Google" }),
    );

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Google hiện chưa sẵn sàng",
    );
    const [, options] = fetchMock.mock.calls[0] ?? [];
    expect(JSON.parse(String(options?.body))).toEqual({
      accountType: "PUBLIC_USER",
    });
  });
});
