import { describe, expect, it } from "vitest";

import { resolveFirebaseAuthDomain } from "@/lib/firebase/client";

describe("resolveFirebaseAuthDomain", () => {
  it("uses the application hostname in production for same-origin redirect auth", () => {
    expect(
      resolveFirebaseAuthDomain(
        "project.firebaseapp.com",
        "decu.tinhhoaviet.org.vn",
        true,
      ),
    ).toBe("decu.tinhhoaviet.org.vn");
  });

  it("keeps the configured Firebase domain outside production", () => {
    expect(
      resolveFirebaseAuthDomain("project.firebaseapp.com", "localhost", false),
    ).toBe("project.firebaseapp.com");
  });
});
