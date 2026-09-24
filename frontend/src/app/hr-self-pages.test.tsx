import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthUserProvider } from "@/lib/auth/user-context";

import AttendancePage from "./(dashboard)/attendance/page";
import LeavePage from "./(dashboard)/leave/page";
import OvertimePage from "./(dashboard)/overtime/page";

vi.mock("@/components/hr/attendance-workspace", () => ({
  AttendanceWorkspace: () => <div>Attendance self-service</div>,
}));
vi.mock("@/components/hr/leave-workspace", () => ({
  LeaveWorkspace: () => <div>Leave self-service</div>,
}));
vi.mock("@/components/hr/overtime-workspace", () => ({
  OvertimeWorkspace: () => <div>Overtime self-service</div>,
}));

const pages = [
  { Page: AttendancePage, label: "Attendance self-service" },
  { Page: LeavePage, label: "Leave self-service" },
  { Page: OvertimePage, label: "Overtime self-service" },
];

describe("HR self-service pages", () => {
  it.each(pages)("allows USER to open $label", ({ Page, label }) => {
    render(
      <AuthUserProvider
        user={{
          id: "employee-user",
          email: "employee@example.com",
          roles: ["USER"],
          accountType: null,
        }}
      >
        <Page />
      </AuthUserProvider>,
    );

    expect(screen.getByText(label)).toBeTruthy();
  });

  it.each(pages)("does not open $label for VIEWER", ({ Page, label }) => {
    render(
      <AuthUserProvider
        user={{
          id: "viewer",
          email: "viewer@example.com",
          roles: ["VIEWER"],
          accountType: null,
        }}
      >
        <Page />
      </AuthUserProvider>,
    );

    expect(screen.queryByText(label)).toBeNull();
  });
});
