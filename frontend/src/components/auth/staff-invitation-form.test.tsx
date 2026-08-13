import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StaffInvitationForm } from "@/components/auth/staff-invitation-form";

const mocks = vi.hoisted(() => ({
  enroll: vi.fn(),
  refresh: vi.fn(),
  replace: vi.fn(),
  signOut: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace, refresh: mocks.refresh }),
}));

const firebaseUser = { getIdToken: vi.fn(async () => "firebase-token") };
vi.mock("@/lib/firebase/client", () => ({
  firebaseConfigured: () => true,
  getFirebaseAuth: () => ({ currentUser: firebaseUser }),
}));

vi.mock("firebase/auth", () => ({
  GoogleAuthProvider: vi.fn(),
  signInWithPopup: vi.fn(async () => ({ user: firebaseUser })),
  signOut: mocks.signOut,
  multiFactor: () => ({
    getSession: vi.fn(async () => ({ id: "mfa-session" })),
    enroll: mocks.enroll,
  }),
  TotpMultiFactorGenerator: {
    generateSecret: vi.fn(async () => ({ secretKey: "TMI-SECRET-KEY" })),
    assertionForEnrollment: (secret: unknown, code: string) => ({
      secret,
      code,
    }),
  },
}));

describe("StaffInvitationForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Object.values(mocks).forEach((mock) => mock.mockReset());
  });

  it("requires TOTP enrollment before sending staff to login", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: { status: "MFA_ENROLLMENT_REQUIRED" },
          meta: { request_id: "request-2" },
        }),
        { status: 202, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<StaffInvitationForm token={"a".repeat(48)} />);

    await userEvent.click(
      screen.getByRole("button", { name: "Xác minh email và tiếp tục" }),
    );
    expect(await screen.findByText("TMI-SECRET-KEY")).toBeDefined();

    await userEvent.type(screen.getByLabelText("Mã xác minh 6 số"), "654321");
    await userEvent.click(
      screen.getByRole("button", { name: "Kích hoạt bảo vệ hai bước" }),
    );

    await waitFor(() => expect(mocks.enroll).toHaveBeenCalledOnce());
    expect(mocks.signOut).toHaveBeenCalledOnce();
    expect(mocks.replace).toHaveBeenCalledWith("/login?mfa=enrolled");
  });
});
