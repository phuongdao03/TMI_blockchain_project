import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DepartmentWorkspace } from "@/components/hr/department-workspace";
import { EmployeeWorkspace } from "@/components/hr/employee-workspace";

const listDepartments = vi.hoisted(() => vi.fn());
const listEmployees = vi.hoisted(() => vi.fn());
const exportDepartments = vi.hoisted(() => vi.fn());
const updateDepartment = vi.hoisted(() => vi.fn());
const exportEmployees = vi.hoisted(() => vi.fn());
const saveWorkbook = vi.hoisted(() => vi.fn());
const listAccounts = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  adminUsersApi: { list: listAccounts },
  employeeInvitationsApi: { create: vi.fn() },
  hrDepartmentApi: {
    list: listDepartments,
    create: vi.fn(),
    update: updateDepartment,
    exportXlsx: exportDepartments,
  },
  hrEmployeeApi: {
    list: listEmployees,
    create: vi.fn(),
    update: vi.fn(),
    exportXlsx: exportEmployees,
  },
}));
vi.mock("@/lib/download", () => ({ saveWorkbook }));

function renderWorkspace(workspace: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>{workspace}</QueryClientProvider>,
  );
}

describe("HR report downloads", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listDepartments.mockResolvedValue({
      data: [{ id: "department-1", code: "ENG", name: "Kỹ thuật" }],
      meta: { total: 1 },
    });
    listEmployees.mockResolvedValue({ data: [], meta: { total: 0 } });
    listAccounts.mockResolvedValue({
      data: [
        {
          id: "user-1",
          fullName: "Lan",
          email: "lan@example.com",
          isEmailVerified: true,
          roles: ["MODERATOR"],
        },
      ],
      meta: { total: 1 },
    });
    exportDepartments.mockResolvedValue(new Blob(["xlsx"]));
    exportEmployees.mockResolvedValue(new Blob(["xlsx"]));
    updateDepartment.mockResolvedValue({
      id: "department-1",
      code: "ENG",
      name: "Phòng Kỹ thuật",
    });
  });

  it("exports departments using the applied search", async () => {
    renderWorkspace(<DepartmentWorkspace />);
    fireEvent.change(screen.getByRole("textbox", { name: "Tìm phòng ban" }), {
      target: { value: "Kỹ thuật" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Tìm kiếm" }));
    fireEvent.click(screen.getByRole("button", { name: "Xuất Excel" }));

    await waitFor(() =>
      expect(exportDepartments).toHaveBeenCalledWith({ search: "Kỹ thuật" }),
    );
    expect(saveWorkbook).toHaveBeenCalledWith(
      expect.any(Blob),
      "hr-departments.xlsx",
    );
  });

  it("lets an admin rename a department without changing its code", async () => {
    renderWorkspace(<DepartmentWorkspace />);
    fireEvent.click(
      await screen.findByRole("button", { name: /Sửa phòng ban/ }),
    );
    fireEvent.change(screen.getByRole("textbox", { name: "Tên phòng ban" }), {
      target: { value: "Phòng Kỹ thuật" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));
    await waitFor(() =>
      expect(updateDepartment).toHaveBeenCalledWith("department-1", {
        name: "Phòng Kỹ thuật",
        description: null,
      }),
    );
  });

  it("exports employees using search, department and status filters", async () => {
    renderWorkspace(<EmployeeWorkspace />);
    await screen.findByRole("option", { name: "Kỹ thuật" });
    fireEvent.change(screen.getByRole("textbox", { name: "Tìm kiếm" }), {
      target: { value: "Minh" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Phòng ban" }), {
      target: { value: "department-1" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Trạng thái" }), {
      target: { value: "ACTIVE" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Áp dụng" }));
    fireEvent.click(screen.getByRole("button", { name: "Xuất Excel" }));

    await waitFor(() =>
      expect(exportEmployees).toHaveBeenCalledWith({
        search: "Minh",
        departmentId: "department-1",
        employmentStatus: "ACTIVE",
      }),
    );
    expect(saveWorkbook).toHaveBeenCalledWith(
      expect.any(Blob),
      "hr-employees.xlsx",
    );
  });

  it("shows existing verified accounts as employee candidates without a search", async () => {
    renderWorkspace(<EmployeeWorkspace />);
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Chọn tài khoản để thêm nhân viên",
      }),
    );
    expect(
      await screen.findByRole("option", { name: "Lan · lan@example.com" }),
    ).toBeDefined();
    expect(listAccounts).toHaveBeenCalledWith(
      expect.objectContaining({ status: "ACTIVE", verified: true }),
    );
  });
});
