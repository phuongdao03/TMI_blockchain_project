"use client";

import { useQuery } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";

import { authApi } from "@/lib/api/client";
import type { AuthUser } from "@/lib/api/types";
import { AuthUserProvider } from "@/lib/auth/user-context";

export function DashboardAuthGuard({
  children,
  initialUser,
}: {
  children: ReactNode;
  initialUser: AuthUser | null;
}) {
  const router = useRouter();
  const { data: user, isPending } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.currentUser,
    initialData: initialUser ?? undefined,
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!isPending && !user) {
      router.replace("/login?next=/dashboard");
    }
  }, [isPending, router, user]);

  if (isPending || !user) {
    return (
      <div
        className="grid min-h-dvh place-items-center bg-background text-neutral-700"
        role="status"
      >
        <span className="flex items-center gap-3">
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          Đang xác thực phiên…
        </span>
      </div>
    );
  }
  return <AuthUserProvider user={user}>{children}</AuthUserProvider>;
}
