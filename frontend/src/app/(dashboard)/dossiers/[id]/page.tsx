import { DossierWorkspace } from "@/components/dossiers/dossier-workspace";

export default async function DossierDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <DossierWorkspace dossierId={id} />;
}
