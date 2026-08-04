"use client";

import { LoaderCircle } from "lucide-react";
import { useState } from "react";

import { ApiError, authApi } from "@/lib/api/client";
import type { AccountType } from "@/lib/api/types";

function oauthErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "Không thể kết nối Google lúc này. Vui lòng thử lại.";
  }
  if (error.code === "OAUTH_PROVIDER_UNAVAILABLE") {
    return "Google hiện chưa sẵn sàng. Vui lòng dùng mật khẩu hoặc thử lại sau.";
  }
  if (error.code === "OAUTH_RATE_LIMITED") {
    return "Bạn đã thử quá nhiều lần. Vui lòng chờ một lát rồi thử lại.";
  }
  return error.message;
}

export function GoogleOAuthButton({
  accountType,
  next,
  label = "Tiếp tục với Google",
}: {
  accountType: AccountType;
  next?: string;
  label?: string;
}) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string>();

  async function startGoogleOAuth() {
    setError(undefined);
    setIsPending(true);
    try {
      const { authorizationUrl } = await authApi.startGoogle(accountType, next);
      window.location.assign(authorizationUrl);
    } catch (cause) {
      setError(oauthErrorMessage(cause));
      setIsPending(false);
    }
  }

  return (
    <div className="space-y-3">
      {error ? (
        <p
          className="rounded-md border border-[#ff8d82]/35 bg-[#3a1b19] px-3.5 py-3 text-sm font-medium text-[#ffb4aa]"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      <button
        className="flex min-h-12 w-full items-center justify-center gap-3 rounded-md border border-[#ad8883]/45 bg-[#171717] px-4 text-sm font-bold text-[#e5e2e1] transition-colors hover:border-[#ffb4aa] hover:bg-[#242222] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ffb4aa] disabled:pointer-events-none disabled:opacity-60"
        disabled={isPending}
        onClick={startGoogleOAuth}
        type="button"
      >
        {isPending ? (
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
        ) : (
          <span
            aria-hidden="true"
            className="grid size-5 place-items-center rounded-sm bg-[#e5e2e1] text-xs font-black text-[#242222]"
          >
            G
          </span>
        )}
        {isPending ? "Đang chuyển tới Google…" : label}
      </button>
    </div>
  );
}
