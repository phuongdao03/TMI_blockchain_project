import { notFound } from "next/navigation";

import { RoleUiPreview } from "@/components/preview/role-ui-preview";
import type { WorkspacePersona } from "@/lib/auth/role-workspaces";

const roles = new Set<WorkspacePersona>([
  "VIEWER",
  "USER",
  "MODERATOR",
  "SUPER_ADMIN",
]);

export default async function RoleUiPreviewPage({
  searchParams,
}: PageProps<"/ui-preview">) {
  if (process.env.NODE_ENV !== "development") notFound();

  const params = await searchParams;
  const requestedRole = params.role;
  const role =
    typeof requestedRole === "string" &&
    roles.has(requestedRole as WorkspacePersona)
      ? (requestedRole as WorkspacePersona)
      : "VIEWER";
  const path = typeof params.path === "string" ? params.path : undefined;

  return <RoleUiPreview role={role} path={path} />;
}
