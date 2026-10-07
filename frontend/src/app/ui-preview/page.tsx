import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { RoleUiPreview } from "@/components/preview/role-ui-preview";
import type { WorkspacePersona } from "@/lib/auth/role-workspaces";

const roles = new Set<WorkspacePersona>([
  "VIEWER",
  "USER",
  "MODERATOR",
  "SUPER_ADMIN",
]);

const roleLabels: Record<WorkspacePersona, string> = {
  VIEWER: "Khách xem",
  USER: "Người dùng",
  MODERATOR: "Moderator",
  SUPER_ADMIN: "Super Admin",
};

function resolveRole(requestedRole: string | string[] | undefined) {
  return typeof requestedRole === "string" &&
    roles.has(requestedRole as WorkspacePersona)
    ? (requestedRole as WorkspacePersona)
    : "VIEWER";
}

export async function generateMetadata({
  searchParams,
}: PageProps<"/ui-preview">): Promise<Metadata> {
  const role = resolveRole((await searchParams).role);
  return {
    title: `Xem thử ${roleLabels[role]} | Tinh Hoa Việt`,
    robots: { index: false, follow: false },
  };
}

export default async function RoleUiPreviewPage({
  searchParams,
}: PageProps<"/ui-preview">) {
  if (process.env.NODE_ENV !== "development") notFound();

  const params = await searchParams;
  const role = resolveRole(params.role);
  const path = typeof params.path === "string" ? params.path : undefined;

  return <RoleUiPreview role={role} path={path} />;
}
