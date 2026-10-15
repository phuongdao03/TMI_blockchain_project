import type { Metadata } from "next";

import { CommunityAdminWorkspace } from "@/components/community/community-admin-workspace";
import { RoleGate } from "@/components/auth/role-gate";

export const metadata: Metadata = {
  title: "Kiểm duyệt cộng đồng",
};

export default function CommunityModerationPage() {
  return (
    <RoleGate
      allowed={["SUPER_ADMIN"]}
      permissions={["community.moderate", "community.manage"]}
    >
      <CommunityAdminWorkspace />
    </RoleGate>
  );
}
