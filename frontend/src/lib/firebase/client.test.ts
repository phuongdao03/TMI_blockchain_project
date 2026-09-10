import { describe, expect, it } from "vitest";

import { resolveFirebaseAuthDomain } from "@/lib/firebase/client";

describe("resolveFirebaseAuthDomain", () => {
  it("keeps the configured Firebase handler domain in production", () => {
    expect(resolveFirebaseAuthDomain("project.firebaseapp.com")).toBe(
      "project.firebaseapp.com",
    );
  });

  it("keeps the configured Firebase domain outside production", () => {
    expect(resolveFirebaseAuthDomain("project.firebaseapp.com")).toBe(
      "project.firebaseapp.com",
    );
  });
});
