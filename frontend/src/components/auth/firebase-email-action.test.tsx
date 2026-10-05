import { render, screen } from "@testing-library/react";
import { StrictMode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FirebaseEmailAction } from "@/components/auth/firebase-email-action";

const mocks = vi.hoisted(() => ({
  applyActionCode: vi.fn(),
  auth: { languageCode: "en" },
}));

vi.mock("firebase/auth", () => ({ applyActionCode: mocks.applyActionCode }));
vi.mock("@/lib/firebase/client", () => ({
  firebaseConfigured: () => true,
  getFirebaseAuth: () => mocks.auth,
}));

describe("FirebaseEmailAction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.auth.languageCode = "en";
  });

  it("verifies the Firebase code once and confirms success in Vietnamese", async () => {
    mocks.applyActionCode.mockResolvedValue(undefined);
    render(
      <StrictMode>
        <FirebaseEmailAction mode="verifyEmail" oobCode="valid-code" />
      </StrictMode>,
    );

    expect(
      await screen.findByText(
        "Email đã được xác minh thành công. Bạn có thể đăng nhập ngay.",
      ),
    ).toBeDefined();
    expect(mocks.applyActionCode).toHaveBeenCalledOnce();
    expect(mocks.applyActionCode).toHaveBeenCalledWith(
      mocks.auth,
      "valid-code",
    );
    expect(mocks.auth.languageCode).toBe("vi");
  });

  it("does not apply an unknown or missing action code", () => {
    render(<FirebaseEmailAction mode="unknown" oobCode="" />);
    expect(screen.getByRole("alert").textContent).toContain(
      "không hợp lệ hoặc đã hết hạn",
    );
    expect(mocks.applyActionCode).not.toHaveBeenCalled();
  });
});
