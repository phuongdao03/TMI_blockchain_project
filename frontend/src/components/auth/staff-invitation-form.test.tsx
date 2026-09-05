import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { StaffInvitationForm } from "@/components/auth/staff-invitation-form";

const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

const firebaseUser = { getIdToken: vi.fn(async () => "firebase-token") };
vi.mock("@/lib/firebase/client", () => ({
  firebaseConfigured: () => true,
  getFirebaseAuth: () => ({}),
}));
vi.mock("firebase/auth", () => ({
  GoogleAuthProvider: vi.fn(),
  signInWithPopup: vi.fn(async () => ({ user: firebaseUser })),
}));

describe("StaffInvitationForm", () => {
  it("activates staff after the invited Firebase email is verified", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: { status: "ACTIVE" },
          meta: { request_id: "request-2" },
        }),
        { status: 202, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<StaffInvitationForm token={"a".repeat(48)} />);

    await userEvent.click(
      screen.getByRole("button", {
        name: "Xác minh email và kích hoạt tài khoản",
      }),
    );

    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/login?invitation=accepted"),
    );
    expect(screen.queryByText(/mã xác minh/i)).toBeNull();
  });
});
