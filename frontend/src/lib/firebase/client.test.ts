import { describe, expect, it } from "vitest";

import { resolveFirebaseAuthDomain } from "@/lib/firebase/client";

describe("resolveFirebaseAuthDomain", () => {
  it("keeps Firebase's configured auth domain in production", () => {
    expect(
      resolveFirebaseAuthDomain(
        "project.firebaseapp.com",
        "decu.tinhhoaviet.org.vn",
        true,
      ),
    ).toBe("project.firebaseapp.com");
  });

  it("keeps the configured Firebase domain outside production", () => {
    expect(
      resolveFirebaseAuthDomain("project.firebaseapp.com", "localhost", false),
    ).toBe("project.firebaseapp.com");
  });
});
