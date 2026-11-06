import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApplicantUpgradeCard } from "@/components/dashboard/applicant-upgrade-card";
import type { AuthUser } from "@/lib/api/types";

const { upgradeToApplicant, claimReferral } = vi.hoisted(() => ({
  upgradeToApplicant: vi.fn(),
  claimReferral: vi.fn(),
}));
vi.mock("@/lib/api/client", () => ({
  authApi: { upgradeToApplicant },
  affiliateApi: { claimReferral },
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe("ApplicantUpgradeCard", () => {
  beforeEach(() => {
    upgradeToApplicant.mockReset();
    claimReferral.mockReset();
    localStorage.clear();
  });

  it("reveals sender choices only after the user starts a submission", async () => {
    const upgraded: AuthUser = {
      id: "user-1",
      email: "viewer@cnsgroup.vn",
      roles: ["USER"],
      accountType: "INDIVIDUAL_APPLICANT",
    };
    upgradeToApplicant.mockResolvedValueOnce(upgraded);
    const onUpgraded = vi.fn();

    render(<ApplicantUpgradeCard onUpgraded={onUpgraded} />);

    expect(screen.queryByLabelText(/Cá nhân/i)).toBeNull();
    fireEvent.click(
      screen.getByRole("button", { name: /Bắt đầu hồ sơ đề cử/i }),
    );
    expect(screen.getByLabelText(/Cá nhân/i)).toBeDefined();
    fireEvent.click(screen.getByLabelText(/Cá nhân/i));
    fireEvent.click(screen.getByRole("button", { name: /Tiếp tục/i }));

    await waitFor(() => {
      expect(upgradeToApplicant).toHaveBeenCalledWith("INDIVIDUAL_APPLICANT");
      expect(onUpgraded).toHaveBeenCalledWith(upgraded);
    });
  });

  it("claims a persisted referral after applicant upgrade", async () => {
    const upgraded: AuthUser = {
      id: "user-1",
      email: "viewer@cnsgroup.vn",
      roles: ["USER"],
      accountType: "INDIVIDUAL_APPLICANT",
    };
    upgradeToApplicant.mockResolvedValueOnce(upgraded);
    claimReferral.mockResolvedValueOnce({ id: "attribution-1" });
    localStorage.setItem(
      "thv.affiliate.referral-attribution",
      JSON.stringify({
        referralCode: "THV-ABC123",
        eventId: "7b6257d9-c9d3-4461-8805-4b88cfaea282",
        clickId: "0d7f1d18-e455-4a7a-9df0-fce15fc9223a",
      }),
    );

    render(<ApplicantUpgradeCard />);
    fireEvent.click(screen.getAllByRole("button")[0]!);
    fireEvent.click(screen.getAllByRole("radio")[0]!);
    fireEvent.click(screen.getAllByRole("button").at(-1)!);

    await waitFor(() => {
      expect(claimReferral).toHaveBeenCalledWith(
        "THV-ABC123",
        "0d7f1d18-e455-4a7a-9df0-fce15fc9223a",
      );
    });
    expect(
      localStorage.getItem("thv.affiliate.referral-attribution"),
    ).toBeNull();
  });
});
