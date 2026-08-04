"use client";

import { ShieldX } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { useAuthUser } from "@/lib/auth/user-context";
import {
  hasAnyRole,
  resolveDefaultWorkspace,
} from "@/lib/auth/role-workspaces";

export function RoleGate({
  allowed,
  children,
}: {
  allowed: readonly string[];
  children: ReactNode;
}) {
  const user = useAuthUser();
  if (!user || !hasAnyRole(user.roles, allowed)) {
    return (
      <section className="mx-auto max-w-2xl rounded-2xl border border-neutral-200 bg-white p-8 text-center">
        <ShieldX
          aria-hidden="true"
          className="mx-auto size-10 text-primary-700"
        />
        <h1 className="mt-4 text-2xl font-bold text-neutral-950">
          Không có quyền truy cập
        </h1>
        <p className="mt-2 text-sm leading-6 text-neutral-600">
          Không gian làm việc hiện tại không bao gồm chức năng này.
        </p>
        <Link
          className="mt-5 inline-flex min-h-11 items-center rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white"
          href={resolveDefaultWorkspace(user?.roles ?? [])}
        >
          Về không gian của tôi
        </Link>
      </section>
    );
  }
  return children;
}
