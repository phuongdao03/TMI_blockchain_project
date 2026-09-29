import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PeopleWorkspace } from "./people-workspace";

const listEmployees = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  hrEmployeeApi: { list: listEmployees },
}));
vi.mock("@/components/admin/staff-account-workspace", () => ({
  StaffAccountWorkspace: ({
    onCreateEmployee,
  }: {
    onCreateEmployee: (account: { id: string; email: string }) => void;
  }) => (
    <button
      onClick={() =>
        onCreateEmployee({ id: "moderator-1", email: "reviewer@example.com" })
      }
      type="button"
    >
      Hồ sơ của reviewer
    </button>
  ),
}));
vi.mock("./employee-workspace", () => ({
  EmployeeWorkspace: ({
    initialSearch,
    linkedAccount,
  }: {
    initialSearch: string;
    linkedAccount: { id: string; email: string } | null;
  }) => (
    <div>
      <span data-testid="search">{initialSearch}</span>
      <span data-testid="linked-account">{linkedAccount?.email ?? "none"}</span>
    </div>
  ),
}));

beforeEach(() => vi.clearAllMocks());

describe("PeopleWorkspace", () => {
  it("opens a prelinked form when the moderator has no employee profile", async () => {
    listEmployees.mockResolvedValue({ data: [] });
    render(<PeopleWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Hồ sơ của reviewer" }));

    await waitFor(() =>
      expect(screen.getByTestId("linked-account").textContent).toBe(
        "reviewer@example.com",
      ),
    );
    expect(listEmployees).toHaveBeenCalledWith({
      search: "reviewer@example.com",
      pageSize: 20,
    });
    expect(
      screen
        .getByRole("tab", { name: "Hồ sơ nhân viên" })
        .getAttribute("aria-selected"),
    ).toBe("true");
  });

  it("opens the existing profile when the moderator already has one", async () => {
    listEmployees.mockResolvedValue({
      data: [{ email: "reviewer@example.com", userId: "moderator-1" }],
    });
    render(<PeopleWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Hồ sơ của reviewer" }));

    await waitFor(() =>
      expect(screen.getByTestId("search").textContent).toBe(
        "reviewer@example.com",
      ),
    );
    expect(screen.getByTestId("linked-account").textContent).toBe("none");
    expect(screen.getByText(/đã liên kết với tài khoản này/)).toBeDefined();
  });
});
