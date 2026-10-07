import { DossierWorkspace } from "@/components/dossiers/dossier-workspace";

export default async function DossierDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ created?: string }>;
}) {
  const { id } = await params;
  const { created } = await searchParams;
  return <DossierWorkspace dossierId={id} justCreated={created === "1"} />;
}
