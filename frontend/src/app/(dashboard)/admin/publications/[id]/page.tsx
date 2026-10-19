import { PublicWorkEditor } from "@/components/admin/public-work-editor";
import { RoleGate } from "@/components/auth/role-gate";
import { WorkspacePageHeader } from "@/components/layout/workspace-page-header";
import { BookOpenText } from "lucide-react";

type AdminPublicationPageProps = {
  params: Promise<{ id: string }>;
};

export default async function AdminPublicationPage({
  params,
}: AdminPublicationPageProps) {
  const { id } = await params;

  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <div className="workspace-screen mx-auto max-w-7xl space-y-6">
        <WorkspacePageHeader
          description="Kiểm tra nội dung, hồ sơ và điều kiện công bố của tác phẩm được chọn."
          icon={BookOpenText}
          section="Nội dung công bố"
          title="Biên tập tác phẩm"
        />
        <PublicWorkEditor initialSelectedId={id} />
      </div>
    </RoleGate>
  );
}
