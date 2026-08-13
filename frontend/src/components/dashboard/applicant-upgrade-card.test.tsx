import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ApplicantUpgradeCard } from "@/components/dashboard/applicant-upgrade-card";
import type { AuthUser } from "@/lib/api/types";

const { upgradeToApplicant } = vi.hoisted(() => ({
  upgradeToApplicant: vi.fn(),
}));
vi.mock("@/lib/api/client", () => ({
  authApi: { upgradeToApplicant },
}));

describe("ApplicantUpgradeCard", () => {
  it("explains the applicant path and upgrades the existing account", async () => {
    const upgraded: AuthUser = {
      id: "user-1",
      email: "viewer@tmigroup.vn",
      roles: ["APPLICANT"],
      accountType: "INDIVIDUAL_APPLICANT",
    };
    upgradeToApplicant.mockResolvedValueOnce(upgraded);
    const onUpgraded = vi.fn();

    render(<ApplicantUpgradeCard onUpgraded={onUpgraded} />);

    expect(screen.getByText(/Không cần tạo tài khoản mới/i)).toBeDefined();
    fireEvent.click(screen.getByLabelText(/Cá nhân/i));
    fireEvent.click(
      screen.getByRole("button", { name: /Bắt đầu gửi tài sản/i }),
    );

    await waitFor(() => {
      expect(upgradeToApplicant).toHaveBeenCalledWith("INDIVIDUAL_APPLICANT");
      expect(onUpgraded).toHaveBeenCalledWith(upgraded);
    });
  });
});
