import { SearchAnalyticsDashboard } from "@/components/admin/search-analytics-dashboard";
import { RoleGate } from "@/components/auth/role-gate";

export default function SearchAnalyticsPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <SearchAnalyticsDashboard />
    </RoleGate>
  );
}
