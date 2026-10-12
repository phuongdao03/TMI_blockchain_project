import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { AccountSettings } from "@/components/account/account-settings";

const getProfile = vi.hoisted(() => vi.fn());
const listOrganizations = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  profileApi: { get: getProfile, update: vi.fn(), updateAvatar: vi.fn() },
  organizationApi: { list: listOrganizations },
}));

it("loads an employee's editable profile without waiting for organizations", async () => {
  getProfile.mockResolvedValue({
    userId: "user-1",
    email: "employee@example.com",
    fullName: "Nhân viên",
    phone: "+84901234567",
    avatarMediaId: null,
    locale: "vi",
    timezone: "Asia/Ho_Chi_Minh",
    employment: {
      employeeCode: "NV-001",
      departmentName: "Thẩm định",
      position: "Kiểm duyệt viên",
      employmentStatus: "ACTIVE",
      joinDate: "2026-10-01",
    },
  });
  listOrganizations.mockRejectedValue(new Error("organization unavailable"));
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <AccountSettings />
    </QueryClientProvider>,
  );
  expect(await screen.findByLabelText("Họ và tên")).toBeDefined();
  expect(screen.getByText("NV-001")).toBeDefined();
  expect(listOrganizations).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("tab", { name: "Tổ chức" }));
  await waitFor(() => expect(listOrganizations).toHaveBeenCalledTimes(1));
});
