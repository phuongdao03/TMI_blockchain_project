"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronLeft, ChevronRight, LoaderCircle, RotateCcw, X } from "lucide-react";
import { useState } from "react";

import { communityAdminApi } from "@/lib/api/client";
import type { CommunityModerationQueuePost } from "@/lib/api/types";

const PAGE_SIZE = 20;

export function CommunityModerationQueue() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const queue = useQuery({
    queryKey: ["community", "admin", "pending", page],
    queryFn: ({ signal }) => communityAdminApi.pendingPosts(page, signal),
  });
  const transition = useMutation({
    mutationFn: ({
      postId,
      action,
      reason,
    }: {
      postId: string;
      action: "publish" | "reject";
      reason: string;
    }) =>
      action === "publish"
        ? communityAdminApi.publishPost(postId, { reason })
        : communityAdminApi.rejectPost(postId, { reason }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["community", "admin", "pending"] });
    },
  });
  const posts = queue.data?.data ?? [];
  const totalPages = Math.max(
    1,
    Math.ceil((queue.data?.meta.total ?? 0) / (queue.data?.meta.pageSize || PAGE_SIZE)),
  );

  function decide(postId: string, action: "publish" | "reject") {
    const reason = reasons[postId]?.trim();
    if (!reason || transition.isPending) return;
    transition.mutate({ postId, action, reason });
  }

  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <header className="border-b border-[var(--theme-border)] pb-6 sm:pb-8">
        <p className="text-xs font-bold tracking-[0.18em] text-[var(--theme-accent)] uppercase">
          Không gian quản trị
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[var(--theme-text)] sm:text-4xl">
          Kiểm duyệt cộng đồng
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--theme-muted)] sm:text-base">
          Xem nội dung đang chờ, ghi lý do và quyết định trước khi bài viết xuất hiện công khai.
        </p>
      </header>

      {queue.isPending ? <QueueSkeleton /> : null}
      {queue.isError ? (
        <div className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6" role="alert">
          <h2 className="font-bold text-[var(--theme-text)]">
            Chưa thể tải hàng đợi kiểm duyệt.
          </h2>
          <p className="mt-2 text-sm text-[var(--theme-muted)]">
            Kiểm tra kết nối hoặc quyền truy cập rồi thử lại.
          </p>
          <button
            className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
            onClick={() => void queue.refetch()}
            type="button"
          >
            <RotateCcw aria-hidden="true" className="size-4" /> Thử tải lại
          </button>
        </div>
      ) : null}
      {queue.data && posts.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[var(--theme-border)] px-5 py-12 text-center sm:py-16">
          <h2 className="text-xl font-bold text-[var(--theme-text)]">
            Hàng đợi đang trống
          </h2>
          <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
            Không có bài viết nào đang chờ kiểm duyệt.
          </p>
        </div>
      ) : null}

      {posts.length > 0 ? (
        <section aria-label="Bài viết chờ kiểm duyệt" aria-busy={transition.isPending}>
          <div className="space-y-4">
            {posts.map((post) => (
              <ModerationCard
                key={post.id}
                onReasonChange={(reason) =>
                  setReasons((current) => ({ ...current, [post.id]: reason }))
                }
                onReject={() => decide(post.id, "reject")}
                onPublish={() => decide(post.id, "publish")}
                pending={transition.isPending}
                post={post}
                reason={reasons[post.id] ?? ""}
              />
            ))}
          </div>
          {transition.isError ? (
            <p className="mt-4 rounded-xl border border-red-300 bg-red-50 p-4 text-sm font-semibold text-red-900" role="alert">
              Không thể cập nhật trạng thái bài viết. Hàng đợi có thể đã thay đổi, vui lòng tải lại.
            </p>
          ) : null}
          {totalPages > 1 ? (
            <nav
              aria-label="Phân trang hàng đợi kiểm duyệt"
              className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--theme-border)] py-5"
            >
              <button
                className={paginationClass}
                disabled={page <= 1}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                type="button"
              >
                <ChevronLeft aria-hidden="true" className="size-4" /> Trang trước
              </button>
              <p aria-live="polite" className="text-sm text-[var(--theme-muted)]">
                Trang {page} / {totalPages}
              </p>
              <button
                className={paginationClass}
                disabled={page >= totalPages}
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                type="button"
              >
                Trang sau <ChevronRight aria-hidden="true" className="size-4" />
              </button>
            </nav>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

function ModerationCard({
  onReasonChange,
  onReject,
  onPublish,
  pending,
  post,
  reason,
}: {
  onReasonChange: (reason: string) => void;
  onReject: () => void;
  onPublish: () => void;
  pending: boolean;
  post: CommunityModerationQueuePost;
  reason: string;
}) {
  const reasonId = `community-reason-${post.id}`;
  return (
    <article className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-semibold text-[var(--theme-muted)]">
        <span className="text-[var(--theme-accent)]">{post.category.name}</span>
        <span aria-hidden="true">·</span>
        <span>{post.author.displayName?.trim() || "Thành viên cộng đồng"}</span>
        <time dateTime={post.submittedAt}>Gửi lúc {formatDate(post.submittedAt)}</time>
      </div>
      <h2 className="mt-3 text-xl font-bold leading-snug text-[var(--theme-text)] sm:text-2xl">
        {post.title}
      </h2>
      <details className="mt-4 rounded-xl border border-[var(--theme-border)] p-4">
        <summary className="cursor-pointer text-sm font-semibold text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]">
          Xem nội dung được gửi
        </summary>
        <p className="mt-3 max-h-72 overflow-y-auto whitespace-pre-wrap break-words text-sm leading-6 text-[var(--theme-muted)]">
          {post.content}
        </p>
      </details>
      <div className="mt-5">
        <label
          className="block text-sm font-semibold text-[var(--theme-text)]"
          htmlFor={reasonId}
        >
          Lý do kiểm duyệt <span className="text-[var(--theme-accent)]">*</span>
        </label>
        <textarea
          className="mt-2 min-h-24 w-full resize-y rounded-xl border border-[var(--theme-border)] bg-[var(--theme-bg)] p-3 text-sm leading-6 text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20"
          id={reasonId}
          maxLength={2000}
          onChange={(event) => onReasonChange(event.target.value)}
          value={reason}
        />
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!reason.trim() || pending}
            onClick={onPublish}
            type="button"
          >
            {pending ? (
              <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
            ) : (
              <Check aria-hidden="true" className="size-4" />
            )}
            Duyệt và đăng bài
          </button>
          <button
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] transition hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!reason.trim() || pending}
            onClick={onReject}
            type="button"
          >
            <X aria-hidden="true" className="size-4" /> Từ chối bài viết
          </button>
        </div>
      </div>
    </article>
  );
}

const paginationClass =
  "inline-flex min-h-11 items-center gap-1 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50";

function QueueSkeleton() {
  return (
    <div aria-label="Đang tải hàng đợi kiểm duyệt" className="space-y-4" role="status">
      {Array.from({ length: 3 }, (_, index) => (
        <div
          aria-hidden="true"
          className="h-52 animate-pulse rounded-2xl bg-[var(--theme-elevated)]"
          key={index}
        />
      ))}
    </div>
  );
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
