"use client";

import { useQueryClient } from "@tanstack/react-query";
import { signOut } from "firebase/auth";
import { LoaderCircle, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { authApi } from "@/lib/api/client";
import { getFirebaseAuth } from "@/lib/firebase/client";

export function LogoutButton() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string>();

  async function logout() {
    setPending(true);
    setError(undefined);
    try {
      await authApi.logout();
      try {
        await signOut(getFirebaseAuth());
      } catch {
        // The authoritative backend session is already revoked.
      }
      queryClient.clear();
      router.replace("/login");
      router.refresh();
    } catch {
      setError("Không thể đăng xuất lúc này. Vui lòng thử lại.");
      setPending(false);
    }
  }

  return (
    <div className="relative">
      <button
        aria-label="Đăng xuất"
        className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-neutral-200 bg-white px-3 text-sm font-semibold text-neutral-600 hover:border-primary-200 hover:text-primary-700 disabled:cursor-wait disabled:opacity-60"
        disabled={pending}
        onClick={() => void logout()}
        type="button"
      >
        {pending ? (
          <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
        ) : (
          <LogOut aria-hidden="true" className="size-4" />
        )}
        <span className="hidden xl:inline">Đăng xuất</span>
      </button>
      {error ? (
        <p
          className="absolute top-12 right-0 z-50 w-64 rounded-lg border border-red-200 bg-white p-3 text-xs font-medium text-red-700 shadow-lg"
          role="alert"
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}
