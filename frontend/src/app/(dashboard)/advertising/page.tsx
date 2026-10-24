import { RoleGate } from "@/components/auth/role-gate";
import { AdvertisingWorkspace } from "@/components/advertising/advertising-workspace";

export default async function AdvertisingPage({
  searchParams,
}: {
  searchParams: Promise<{ dossierId?: string | string[] }>;
}) {
  const params = await searchParams;
  const dossierId = Array.isArray(params.dossierId)
    ? params.dossierId[0]
    : params.dossierId;

  return (
    <RoleGate allowed={["USER", "SUPER_ADMIN"]}>
      <AdvertisingWorkspace initialDossierId={dossierId} />
    </RoleGate>
  );
}
