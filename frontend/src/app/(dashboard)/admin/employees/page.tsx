import { RoleGate } from "@/components/auth/role-gate";
import { PeopleWorkspace } from "@/components/hr/people-workspace";

export default async function AdminEmployeesPage({
  searchParams,
}: {
  searchParams: Promise<{
    view?: string | string[];
    account?: string | string[];
  }>;
}) {
  const params = await searchParams;
  const initialView = params.view === "employees" ? "employees" : "accounts";
  const initialAccountSearch =
    initialView === "employees" && typeof params.account === "string"
      ? params.account.trim()
      : "";

  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["hr.employees.read"]}>
      <PeopleWorkspace
        initialAccountSearch={initialAccountSearch}
        initialView={initialView}
      />
    </RoleGate>
  );
}
