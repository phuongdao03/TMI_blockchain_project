"use client";

import { UsersRound } from "lucide-react";

import { WorkspacePageHeader } from "@/components/layout/workspace-page-header";
import { useAuthUser } from "@/lib/auth/user-context";

import { AdminAffiliateCommissions } from "./admin-affiliate-commissions";
import { AdminAffiliateProfiles } from "./admin-affiliate-profiles";
import { AdminAffiliateRules } from "./admin-affiliate-rules";

export function AdminAffiliateWorkspace() {
  const user = useAuthUser();
  const roles = user?.roles ?? [];
  const permissions = user?.permissions ?? [];
  const isSuperAdmin = roles.includes("SUPER_ADMIN");
  const canManageProfiles = isSuperAdmin || permissions.includes("affiliate.profiles.manage");
  const canReviewCommissions = isSuperAdmin || permissions.includes("affiliate.commissions.approve");
  const canManageRules = isSuperAdmin || permissions.includes("affiliate.rules.manage");
  const canAccess = canManageProfiles || canReviewCommissions || canManageRules;

  return (
    <main className="workspace-screen mx-auto max-w-6xl space-y-7 pb-12">
      <WorkspacePageHeader
        description="Tra cứu hồ sơ giới thiệu, duyệt hoa hồng và quản lý chính sách chi trả."
        icon={UsersRound}
        section="Tài chính"
        title="Quản trị tiếp thị liên kết"
      />
      {!canAccess ? (
        <p role="alert" className="rounded-xl border border-red-300 p-4 text-sm text-red-700">
          Bạn không có quyền quản lý chương trình tiếp thị liên kết.
        </p>
      ) : (
        <div className="space-y-8">
          {canManageProfiles ? <AdminAffiliateProfiles /> : null}
          {canReviewCommissions ? <AdminAffiliateCommissions /> : null}
          {canManageRules ? <AdminAffiliateRules /> : null}
        </div>
      )}
    </main>
  );
}
