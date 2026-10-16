import { describe, expect, it } from "vitest";

import {
  hasAnyRole,
  resolveDefaultWorkspace,
  resolveAdminEntryPoint,
  resolveWorkspacePersona,
} from "@/lib/auth/role-workspaces";

describe("role workspaces", () => {
  it("opens every role in the personal workspace by default", () => {
    for (const roles of [
      ["VIEWER"],
      ["USER"],
      ["MODERATOR"],
      ["SUPER_ADMIN"],
      ["USER", "SUPER_ADMIN"],
    ]) {
      expect(resolveDefaultWorkspace(roles)).toBe("/workspace");
    }
    expect(resolveDefaultWorkspace(["USER"], ["payments.read"])).toBe(
      "/workspace",
    );
    expect(resolveDefaultWorkspace(["USER"], ["users.read"])).toBe(
      "/workspace",
    );
  });

  it("exposes an explicit permitted admin entry point", () => {
    expect(resolveAdminEntryPoint(["USER"], ["payments.read"])).toEqual({
      href: "/admin/payments",
      label: "Khu vực quản trị",
    });
    expect(resolveAdminEntryPoint(["SUPER_ADMIN"])).toEqual({
      href: "/admin",
      label: "Khu vực quản trị",
    });
    expect(resolveAdminEntryPoint(["USER"], [])).toBeNull();
    expect(resolveAdminEntryPoint(["USER"], ["review.assign"])).toBeNull();
    expect(
      resolveAdminEntryPoint(["USER"], ["hr.attendance.worksites.manage"])
        ?.href,
    ).toBe("/admin/attendance/worksites");
  });

  it("exposes moderator administration only with its permission", () => {
    expect(resolveAdminEntryPoint(["MODERATOR"])).toBeNull();
    expect(
      resolveAdminEntryPoint(["MODERATOR"], ["community.moderate"]),
    ).toEqual({
      href: "/admin/community",
      label: "Khu vực quản trị",
    });
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
