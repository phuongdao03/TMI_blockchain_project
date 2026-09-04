import { describe, expect, it } from "vitest";

import {
  hasAnyRole,
  resolveDefaultWorkspace,
  resolvePublicHeaderAction,
  resolveWorkspacePersona,
} from "@/lib/auth/role-workspaces";

describe("role workspaces", () => {
  it("routes the four product roles to their focused workspaces", () => {
    expect(resolveDefaultWorkspace(["VIEWER"])).toBe("/dashboard");
    expect(resolveDefaultWorkspace(["USER"])).toBe("/dashboard");
    expect(resolveDefaultWorkspace(["MODERATOR"])).toBe("/reviews");
    expect(resolveDefaultWorkspace(["SUPER_ADMIN"])).toBe("/admin");
    expect(resolveDefaultWorkspace(["USER"], ["payments.read"])).toBe(
      "/admin/payments",
    );
    expect(resolveDefaultWorkspace(["USER"], ["users.read"])).toBe(
      "/admin/users",
    );
  });

  it("returns scoped staff from public pages to their assigned operation", () => {
    const action = resolvePublicHeaderAction(["USER"], ["payments.read"]);

    expect(action.href).toBe("/admin/payments");
    expect(action.label).toBe("Khu vực làm việc");
    expect(action.label).not.toMatch(/^Quay lại/i);
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
