import { describe, expect, it } from "vitest";

import {
  hasAnyRole,
  resolveDefaultWorkspace,
  resolveWorkspacePersona,
} from "@/lib/auth/role-workspaces";

describe("role workspaces", () => {
  it("routes the four product roles to their focused workspaces", () => {
    expect(resolveDefaultWorkspace(["VIEWER"])).toBe("/dashboard");
    expect(resolveDefaultWorkspace(["USER"])).toBe("/dashboard");
    expect(resolveDefaultWorkspace(["MODERATOR"])).toBe("/reviews");
    expect(resolveDefaultWorkspace(["SUPER_ADMIN"])).toBe("/admin");
  });

  it("keeps submission actions restricted to users", () => {
    expect(hasAnyRole(["USER"], ["USER"])).toBe(true);
    expect(hasAnyRole(["VIEWER"], ["USER"])).toBe(false);
  });

  it("exposes only the four product personas", () => {
    expect(resolveWorkspacePersona(["VIEWER"])).toBe("VIEWER");
    expect(resolveWorkspacePersona(["USER"])).toBe("USER");
    expect(resolveWorkspacePersona(["MODERATOR"])).toBe("MODERATOR");
    expect(resolveWorkspacePersona(["SUPER_ADMIN"])).toBe("SUPER_ADMIN");
  });
});
