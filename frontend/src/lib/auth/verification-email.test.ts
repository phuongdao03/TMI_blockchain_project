import type { User } from "firebase/auth";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, authApi } from "@/lib/api/client";
import { deliverVerificationEmail } from "@/lib/auth/verification-email";

const fallback = vi.hoisted(() => vi.fn());
vi.mock("firebase/auth", () => ({ sendEmailVerification: fallback }));
const user = { getIdToken: async () => "test-token" } as User;

beforeEach(() => {
  vi.restoreAllMocks();
  fallback.mockReset();
});
describe("verification delivery", () => {
  it("uses Firebase delivery when branded delivery is unavailable", async () => {
    vi.spyOn(authApi, "sendFirebaseVerificationEmail").mockRejectedValue(
      new ApiError("Unavailable", "UNAVAILABLE", 503),
    );
    fallback.mockResolvedValue(undefined);
    await deliverVerificationEmail(user);
    expect(fallback).toHaveBeenCalledWith(user);
  });
  it.each([400, 401, 429])(
    "preserves authoritative rejection %s",
    async (status) => {
      const error = new ApiError("Rejected", "REJECTED", status);
      vi.spyOn(authApi, "sendFirebaseVerificationEmail").mockRejectedValue(
        error,
      );
      await expect(deliverVerificationEmail(user)).rejects.toBe(error);
      expect(fallback).not.toHaveBeenCalled();
    },
  );
  it("reports failure when both delivery services fail", async () => {
    vi.spyOn(authApi, "sendFirebaseVerificationEmail").mockRejectedValue(
      new Error("offline"),
    );
    fallback.mockRejectedValue(new Error("delivery failed"));
    await expect(deliverVerificationEmail(user)).rejects.toThrow(
      "delivery failed",
    );
  });
});
