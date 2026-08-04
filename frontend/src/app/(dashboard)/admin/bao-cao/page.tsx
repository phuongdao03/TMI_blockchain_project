import { ContentReportWorkspace } from "@/components/admin/content-report-workspace";
import { RoleGate } from "@/components/auth/role-gate";

export default function ContentReportsPage() {
  return (
    <RoleGate allowed={["CONTENT_ADMIN", "SUPER_ADMIN"]}>
      <ContentReportWorkspace />
    </RoleGate>
  );
}
