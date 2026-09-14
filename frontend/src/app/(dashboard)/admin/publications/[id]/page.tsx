import { PublicWorkEditor } from "@/components/admin/public-work-editor";
import { RoleGate } from "@/components/auth/role-gate";

type AdminPublicationPageProps = {
  params: Promise<{ id: string }>;
};

export default async function AdminPublicationPage({
  params,
}: AdminPublicationPageProps) {
  const { id } = await params;

  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <div className="mx-auto max-w-7xl space-y-6">
        <header>
          <p className="text-sm font-bold tracking-[0.16em] text-primary-700 uppercase">
            Nội dung công bố
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight">
            Biên tập tác phẩm
          </h1>
        </header>
        <PublicWorkEditor initialSelectedId={id} />
      </div>
    </RoleGate>
  );
}
