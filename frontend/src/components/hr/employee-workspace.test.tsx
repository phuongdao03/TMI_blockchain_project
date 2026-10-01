import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EmployeeWorkspace } from "./employee-workspace";

const listAccounts = vi.hoisted(() => vi.fn());
const createEmployee = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  adminUsersApi: { list: listAccounts },
  employeeInvitationsApi: { create: vi.fn() },
  hrDepartmentApi: {
    list: vi.fn().mockResolvedValue({
      data: [{ id: "department-1", name: "Kiểm duyệt" }],
    }),
  },
  hrEmployeeApi: {
    list: vi.fn().mockResolvedValue({ data: [], meta: { total: 0 } }),
    create: createEmployee,
    exportXlsx: vi.fn(),
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
  listAccounts.mockResolvedValue({
    data: [
      {
        id: "moderator-1",
        email: "reviewer@example.com",
        fullName: "Nguyễn Kiểm Duyệt",
        status: "ACTIVE",
        isEmailVerified: true,
        roles: ["MODERATOR"],
      },
    ],
  });
  createEmployee.mockResolvedValue({ id: "employee-1" });
});

describe("EmployeeWorkspace", () => {
  it("requires a linked account when opened from attendance setup", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <EmployeeWorkspace initialAccountSearch="reviewer@example.com" />
      </QueryClientProvider>,
    );
    expect(await screen.findByText(/Đang tìm tài khoản/)).toBeDefined();
    expect(
      (screen.getByRole("button", { name: "Tạo hồ sơ" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    await screen.findByRole("option", { name: /reviewer@example.com/ });
    fireEvent.change(screen.getByLabelText("Liên kết tài khoản"), {
      target: { value: "moderator-1" },
    });
    expect(
      (screen.getByRole("button", { name: "Tạo hồ sơ" }) as HTMLButtonElement)
        .disabled,
    ).toBe(false);
  });

  it("creates a linked employee profile from an existing moderator account", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <EmployeeWorkspace
          linkedAccount={{ id: "moderator-1", email: "reviewer@example.com" }}
        />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText(/Đang tạo hồ sơ nhân viên cho/),
    ).toBeDefined();
    expect((screen.getByLabelText("Email") as HTMLInputElement).value).toBe(
      "reviewer@example.com",
    );
    await waitFor(() =>
      expect(
        (screen.getByLabelText("Họ và tên") as HTMLInputElement).value,
      ).toBe("Nguyễn Kiểm Duyệt"),
    );
    fireEvent.change(screen.getByLabelText("Mã nhân viên"), {
      target: { value: "NV001" },
    });
    fireEvent.change(screen.getAllByLabelText("Phòng ban")[1]!, {
      target: { value: "department-1" },
    });
    fireEvent.change(screen.getByLabelText("Vị trí"), {
      target: { value: "Kiểm duyệt viên" },
    });
    fireEvent.change(screen.getByLabelText("Ngày vào làm"), {
      target: { value: "2026-09-29" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Tạo hồ sơ" }));

    await waitFor(() =>
      expect(createEmployee).toHaveBeenCalledWith(
        expect.objectContaining({
          userId: "moderator-1",
          email: "reviewer@example.com",
          fullName: "Nguyễn Kiểm Duyệt",
          employeeCode: "NV001",
          departmentId: "department-1",
          joinDate: "2026-09-29",
        }),
      ),
    );
  });
});
