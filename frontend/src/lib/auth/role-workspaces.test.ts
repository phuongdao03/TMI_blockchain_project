import { describe, expect, it } from "vitest";

import {
  hasAnyRole,
  resolveDefaultWorkspace,
  resolveWorkspacePersona,
} from "@/lib/auth/role-workspaces";

describe("role workspaces", () => {
  it("prioritizes privileged workspaces for multi-role users", () => {
    expect(resolveDefaultWorkspace(["APPLICANT", "CONTENT_ADMIN"])).toBe("/admin/noi-dung");
    expect(resolveDefaultWorkspace(["REVIEWER", "SUPER_ADMIN"])).toBe("/admin/dashboard");
  });

  it("keeps applicant actions restricted to applicant roles", () => {
    expect(hasAnyRole(["APPLICANT"], ["APPLICANT", "ORG_MANAGER"])).toBe(true);
    expect(hasAnyRole(["REVIEWER"], ["APPLICANT", "ORG_MANAGER"])).toBe(false);
  });

  it("separates public discovery from applicant and staff workspaces", () => {
    expect(resolveWorkspacePersona(["PUBLIC_USER"])).toBe("PUBLIC");
    expect(resolveWorkspacePersona(["APPLICANT"])).toBe("APPLICANT");
    expect(resolveWorkspacePersona(["REVIEWER"])).toBe("REVIEWER");
    expect(resolveWorkspacePersona(["COUNCIL_MEMBER"])).toBe("COUNCIL");
    expect(resolveWorkspacePersona(["CONTENT_ADMIN"])).toBe("ADMIN");
    expect(resolveWorkspacePersona(["SUPER_ADMIN"])).toBe("SUPER_ADMIN");
  });
});
