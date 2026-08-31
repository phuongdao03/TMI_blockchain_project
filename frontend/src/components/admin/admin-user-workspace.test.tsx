import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { AdminUserWorkspace } from "@/components/admin/admin-user-workspace";
import { AuthUserProvider } from "@/lib/auth/user-context";
import { adminUsersApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  adminUsersApi: { list: vi.fn(), changeStatus: vi.fn() },
  ApiError: class extends Error {},
}));

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <AuthUserProvider
        user={{
          id: "admin-1",
          email: "admin@thv.vn",
          roles: ["SUPER_ADMIN"],
          permissions: ["users.read", "users.suspend"],
          accountType: null,
        }}
      >
        {children}
      </AuthUserProvider>
    </QueryClientProvider>
  );
}

describe("AdminUserWorkspace", () => {
  it("renders real paginated data for desktop and mobile and audits suspension", async () => {
    vi.mocked(adminUsersApi.list).mockResolvedValue({
      success: true,
      data: [
        {
          id: "user-1",
          email: "an@example.com",
          fullName: "Nguyen Van An",
          status: "ACTIVE",
          isEmailVerified: true,
          providers: ["GOOGLE"],
          roles: ["USER"],
          createdAt: "2026-08-20T09:00:00Z",
          lastLoginAt: "2026-08-29T09:00:00Z",
          disabledAt: null,
          deletedAt: null,
        },
      ],
      meta: { request_id: "request-1", page: 1, pageSize: 20, total: 1 },
    });
    vi.mocked(adminUsersApi.changeStatus).mockResolvedValue(undefined as never);

    render(<AdminUserWorkspace />, { wrapper: Wrapper });

    expect(await screen.findAllByText("Nguyen Van An")).toHaveLength(2);
    expect(screen.getByTestId("admin-users-table").className).toContain("hidden");
    expect(screen.getByTestId("admin-users-mobile").className).toContain("md:hidden");

    fireEvent.click(
      screen.getAllByRole("button", { name: "Tạm đình chỉ" })[0]!,
    );
    fireEvent.change(screen.getByLabelText("Lý do thay đổi trạng thái"), {
      target: { value: "Phat hien dang nhap bat thuong" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận đình chỉ" }));

    await waitFor(() =>
      expect(adminUsersApi.changeStatus).toHaveBeenCalledWith("user-1", {
        status: "SUSPENDED",
        expectedStatus: "ACTIVE",
        reason: "Phat hien dang nhap bat thuong",
      }),
    );
  });
});
