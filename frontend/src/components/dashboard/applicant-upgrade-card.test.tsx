import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApplicantUpgradeCard } from "@/components/dashboard/applicant-upgrade-card";
import type { AuthUser } from "@/lib/api/types";

const { upgradeToApplicant } = vi.hoisted(() => ({
  upgradeToApplicant: vi.fn(),
}));
vi.mock("@/lib/api/client", () => ({
  authApi: { upgradeToApplicant },
}));

describe("ApplicantUpgradeCard", () => {
  beforeEach(() => {
    upgradeToApplicant.mockReset();
  });

  it("reveals sender choices only after the user starts a submission", async () => {
    const upgraded: AuthUser = {
      id: "user-1",
      email: "viewer@tmigroup.vn",
      roles: ["USER"],
      accountType: "INDIVIDUAL_APPLICANT",
    };
    upgradeToApplicant.mockResolvedValueOnce(upgraded);
    const onUpgraded = vi.fn();

    render(<ApplicantUpgradeCard onUpgraded={onUpgraded} />);

    expect(screen.queryByLabelText(/Cá nhân/i)).toBeNull();
    fireEvent.click(
      screen.getByRole("button", { name: /Gửi tác phẩm hoặc hồ sơ/i }),
    );
    expect(screen.getByLabelText(/Cá nhân/i)).toBeDefined();
    fireEvent.click(screen.getByLabelText(/Cá nhân/i));
    fireEvent.click(screen.getByRole("button", { name: /Tiếp tục/i }));

    await waitFor(() => {
      expect(upgradeToApplicant).toHaveBeenCalledWith("INDIVIDUAL_APPLICANT");
      expect(onUpgraded).toHaveBeenCalledWith(upgraded);
    });
  });
});
