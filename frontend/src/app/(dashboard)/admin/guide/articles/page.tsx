import { GuideArticleWorkspace } from "@/components/admin/guide-article-workspace";
import { RoleGate } from "@/components/auth/role-gate";

export default function AdminGuideArticlesPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <GuideArticleWorkspace />
    </RoleGate>
  );
}
