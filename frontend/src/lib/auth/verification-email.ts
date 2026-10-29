import { sendEmailVerification, type User } from "firebase/auth";
import { ApiError, authApi } from "@/lib/api/client";

export async function deliverVerificationEmail(user: User): Promise<void> {
  try {
    await authApi.sendFirebaseVerificationEmail(await user.getIdToken());
  } catch (error) {
    // Identity/rate-limit errors are authoritative; fallback only on delivery failure.
    if (error instanceof ApiError && error.status < 500 && error.status !== 408)
      throw error;
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      await Promise.race([
        sendEmailVerification(user),
        new Promise<never>((_, reject) => {
          timer = setTimeout(
            () => reject(new Error("VERIFICATION_DELIVERY_TIMEOUT")),
            15_000,
          );
        }),
      ]);
    } finally {
      if (timer) clearTimeout(timer);
    }
  }
}
