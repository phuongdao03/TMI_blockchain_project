"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, BellRing, LoaderCircle, RotateCcw } from "lucide-react";
import Link from "next/link";

import { communityApi } from "@/lib/api/client";
import { useAuthStatus, useAuthUser } from "@/lib/auth/user-context";

export function CommunityPostFollowAction({
  postId,
  slug,
}: {
  postId: string;
  slug: string;
}) {
  const user = useAuthUser();
  const authStatus = useAuthStatus();
  const queryClient = useQueryClient();
  const queryKey = [
    "community",
    "post-follow",
    postId,
    user?.id ?? "anonymous",
  ];
  const state = useQuery({
    queryKey,
    queryFn: ({ signal }) => communityApi.postFollowState(postId, signal),
    enabled: authStatus === "authenticated" && Boolean(user),
    staleTime: 30_000,
  });
  const updateFollow = useMutation({
    mutationFn: () =>
      state.data?.isFollowing
        ? communityApi.unfollowPost(postId)
        : communityApi.followPost(postId),
    onSuccess: (result) => {
      queryClient.setQueryData(queryKey, result);
      void queryClient.invalidateQueries({
        queryKey: ["community", "posts"],
      });
    },
  });

  if (authStatus === "loading") {
    return (
      <p className="text-sm text-[var(--theme-muted)]" role="status">
        Đang xác minh tài khoản…
      </p>
    );
  }

  if (authStatus === "error") {
    return (
      <p className="text-sm text-[var(--theme-muted)]" role="alert">
        Chưa thể xác minh tài khoản để theo dõi chủ đề.
      </p>
    );
  }

  if (!user) {
    const postPath = `/community/posts/${encodeURIComponent(slug)}`;
    return (
      <Link
        className={actionClass(false)}
        href={`/login?next=${encodeURIComponent(postPath)}`}
      >
        <Bell aria-hidden="true" className="size-4" />
        Đăng nhập để theo dõi chủ đề
      </Link>
    );
  }

  if (state.isPending) {
    return (
      <p
        className="inline-flex min-h-10 items-center gap-2 text-sm text-[var(--theme-muted)]"
        role="status"
      >
        <LoaderCircle
          aria-hidden="true"
          className="size-4 motion-safe:animate-spin"
        />
        Đang tải trạng thái theo dõi…
      </p>
    );
  }

  if (state.isError) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm text-[var(--theme-muted)]" role="alert">
          Chưa thể tải trạng thái theo dõi.
        </p>
        <button
          className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-semibold text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          onClick={() => void state.refetch()}
          type="button"
        >
          <RotateCcw aria-hidden="true" className="size-4" /> Thử lại
        </button>
      </div>
    );
  }

  const isFollowing = state.data?.isFollowing ?? false;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        aria-pressed={isFollowing}
        className={actionClass(isFollowing)}
        disabled={updateFollow.isPending}
        onClick={() => updateFollow.mutate()}
        type="button"
      >
        {updateFollow.isPending ? (
          <LoaderCircle
            aria-hidden="true"
            className="size-4 motion-safe:animate-spin"
          />
        ) : isFollowing ? (
          <BellRing aria-hidden="true" className="size-4" />
        ) : (
          <Bell aria-hidden="true" className="size-4" />
        )}
        {isFollowing ? "Đang theo dõi chủ đề" : "Theo dõi chủ đề"}
      </button>
      {updateFollow.isError ? (
        <p className="text-sm font-semibold text-red-700" role="alert">
          Chưa thể cập nhật. Hãy thử lại.
        </p>
      ) : null}
    </div>
  );
}

function actionClass(active: boolean): string {
  return [
    "inline-flex min-h-10 items-center gap-2 rounded-lg border px-3 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-60",
    active
      ? "border-[var(--theme-accent)] bg-[var(--theme-accent)]/10 text-[var(--theme-accent)]"
      : "border-[var(--theme-border)] text-[var(--theme-text)] hover:border-[var(--theme-accent)]",
  ].join(" ");
}
