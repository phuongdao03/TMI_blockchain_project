import { FeeManagementWorkspace } from "@/components/admin/fee-management-workspace";

export default async function AdminPaymentsPage({
  searchParams,
}: PageProps<"/admin/payments">) {
  const { dossierId } = await searchParams;
  return (
    <FeeManagementWorkspace
      initialDossierId={typeof dossierId === "string" ? dossierId : undefined}
    />
  );
}
