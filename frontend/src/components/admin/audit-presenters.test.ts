import { describe, expect, it } from "vitest";

import {
  auditEventSummary,
  auditTargetLabel,
} from "@/components/admin/audit-presenters";
import type { AuditLogItem } from "@/lib/api/types";

const base: AuditLogItem = {
  id: "audit-1",
  actorUserId: null,
  actorType: "USER",
  actorService: null,
  action: "hr.employee.updated",
  resourceType: "employee",
  resourceId: "internal-uuid",
  before: null,
  after: { employee_code: "NV-001" },
  requestId: "request-1",
  integrityStatus: "VERIFIED",
  retentionUntil: null,
  createdAt: "2026-09-28T00:00:00Z",
};

describe("audit presenters", () => {
  it("describes a personnel update using a business identifier", () => {
    expect(auditEventSummary(base)).toBe("Đã cập nhật hồ sơ nhân viên");
    expect(auditTargetLabel(base)).toBe("Nhân viên · NV-001");
  });

  it("describes a published article by its title", () => {
    const row = {
      ...base,
      action: "cms.post.published",
      resourceType: "cms_post",
      after: { title: "Tin mới" },
    };
    expect(auditEventSummary(row)).toBe("Đã xuất bản bài viết");
    expect(auditTargetLabel(row)).toBe("Bài viết · Tin mới");
  });
});
