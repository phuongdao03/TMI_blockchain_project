"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, RotateCcw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { communityApi, communityMemberApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import type { CommunityOwnerPostStatus } from "@/lib/api/types";

const PAGE_SIZE = 20;
const statusFilters: { value?: CommunityOwnerPostStatus; label: string }[] = [
  { label: "Tất cả" },
  { value: "DRAFT", label: "Bản nháp" },
  { value: "PENDING", label: "Chờ xử lý (bài viết cũ)" },
  { value: "REJECTED", label: "Cần chỉnh sửa" },
  { value: "PUBLISHED", label: "Đã đăng" },
  { value: "HIDDEN", label: "Đã gỡ" },
];

export function CommunityMinePosts({
  status,
  page = 1,
}: {
  status?: CommunityOwnerPostStatus;
  page?: number;
}) {
  const user = useAuthUser();
  const queryClient = useQueryClient();
  const queryKey = [
    "community",
    "mine",
    "posts",
    status ?? "all",
    page,
    user?.id ?? "anonymous",
  ] as const;
  const posts = useQuery({
    queryKey,
    queryFn: ({ signal }) =>
      communityMemberApi.myPosts({ status, page, pageSize: PAGE_SIZE }, signal),
    staleTime: 20_000,
  });
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const remove = useMutation({
    mutationFn: (postId: string) => communityApi.deletePost(postId),
    onSuccess: async () => {
      setConfirmDeleteId(null);
      await queryClient.invalidateQueries({
        queryKey: ["community", "mine", "posts"],
      });
    },
  });
  const totalPages = Math.max(
    1,
    Math.ceil(
      (posts.data?.meta.total ?? 0) / (posts.data?.meta.pageSize || PAGE_SIZE),
    ),
  );

  return (
    <main className="public-theme-surface min-h-[calc(100dvh-5rem)]">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold tracking-[0.18em] text-[var(--theme-accent)] uppercase">
              Không gian thành viên
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-[var(--theme-text)] sm:text-4xl">
              Bài viết của tôi
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
              Theo dõi bản nháp, bài cũ còn chờ xử lý và nội dung đã đăng.
            </p>
          </div>
          <Link
            className="inline-flex min-h-11 items-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
            href="/community/new"
          >
            Viết bài mới
          </Link>
        </div>

        <nav
          aria-label="Lọc trạng thái bài viết"
          className="mt-6 flex gap-2 overflow-x-auto border-b border-[var(--theme-border)] pb-3"
        >
          {statusFilters.map((filter) => {
            const active = status === filter.value;
            const params = new URLSearchParams();
            if (filter.value) params.set("status", filter.value);
            params.set("page", "1");
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={`inline-flex min-h-10 shrink-0 items-center rounded-full border px-4 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] ${active ? "border-[var(--theme-accent)] bg-[var(--theme-accent)] text-[var(--theme-accent-contrast)]" : "border-[var(--theme-border)] text-[var(--theme-muted)] hover:text-[var(--theme-text)]"}`}
                href={`/community/mine?${params.toString()}`}
                key={filter.label}
              >
                {filter.label}
              </Link>
            );
          })}
        </nav>

        {posts.isPending ? (
          <p
            aria-busy="true"
            className="mt-8 flex items-center gap-2 text-sm text-[var(--theme-muted)]"
            role="status"
          >
            <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
            Đang tải bài viết của bạn…
          </p>
        ) : null}
        {posts.isError ? (
          <section
            className="mt-8 rounded-2xl border border-red-300 bg-red-50 p-5 text-red-900"
            role="alert"
          >
            <p className="font-semibold">Chưa thể tải danh sách bài viết.</p>
            <button
              className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-lg border border-red-300 px-3 text-sm font-bold focus-visible:outline-2 focus-visible:outline-offset-2"
              onClick={() => void posts.refetch()}
              type="button"
            >
              <RotateCcw aria-hidden="true" className="size-4" />
              Thử lại
            </button>
          </section>
        ) : null}
        {posts.data?.data.length === 0 ? (
          <p
            className="mt-8 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6 text-sm leading-6 text-[var(--theme-muted)]"
            role="status"
          >
            Chưa có bài viết nào trong trạng thái này.
          </p>
        ) : null}

        {posts.data?.data.length ? (
          <ol className="mt-5 space-y-3">
            {posts.data.data.map((post) => {
              const editable =
                post.status === "DRAFT" ||
                post.status === "REJECTED" ||
                post.status === "PUBLISHED" ||
                post.status === "HIDDEN";
              const href = `/community/new?postId=${encodeURIComponent(post.id)}`;
              return (
                <li
                  className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-6"
                  key={post.id}
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <p className="text-xs font-bold tracking-wide text-[var(--theme-accent)]">
                        {statusLabel(post.status)}
                      </p>
                      <h2 className="mt-2 break-words text-xl font-bold leading-snug text-[var(--theme-text)]">
                        {post.title || "Bài viết chưa có tiêu đề"}
                      </h2>
                      <p className="mt-2 text-sm text-[var(--theme-muted)]">
                        {post.category.name} <span aria-hidden="true">·</span>{" "}
                        Cập nhật {formatDate(post.updatedAt)}
                      </p>
                      {post.status === "REJECTED" && post.moderationReason ? (
                        <p className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
                          <span className="font-bold">Góp ý kiểm duyệt:</span>{" "}
                          {post.moderationReason}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex shrink-0 flex-wrap gap-2">
                      {editable ? (
                        <Link
                          aria-label={`Tiếp tục chỉnh sửa: ${post.title}`}
                          className="inline-flex min-h-10 items-center rounded-lg border border-[var(--theme-border)] px-3 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                          href={href}
                        >
                          Tiếp tục chỉnh sửa
                        </Link>
                      ) : null}
                      {post.status === "PUBLISHED" ? (
                        <Link
                          aria-label={`Xem bài đã đăng: ${post.title}`}
                          className="inline-flex min-h-10 items-center rounded-lg border border-[var(--theme-border)] px-3 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                          href={`/community/posts/${encodeURIComponent(post.slug)}`}
                        >
                          Xem bài đã đăng
                        </Link>
                      ) : null}
                      {editable && confirmDeleteId === post.id ? (
                        <>
                          <button
                            className="inline-flex min-h-10 items-center rounded-lg bg-red-700 px-3 text-sm font-bold text-white focus-visible:outline-2 focus-visible:outline-offset-2"
                            disabled={remove.isPending}
                            onClick={() => remove.mutate(post.id)}
                            type="button"
                          >
                            {remove.isPending
                              ? "Đang xóa…"
                              : `Xác nhận xóa: ${post.title}`}
                          </button>
                          <button
                            className="min-h-10 rounded-lg px-3 text-sm font-semibold text-[var(--theme-muted)] underline focus-visible:outline-2 focus-visible:outline-offset-2"
                            onClick={() => setConfirmDeleteId(null)}
                            type="button"
                          >
                            Hủy
                          </button>
                        </>
                      ) : editable ? (
                        <button
                          aria-label={`Xóa bài: ${post.title}`}
                          className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-semibold text-red-700 underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2"
                          onClick={() => setConfirmDeleteId(post.id)}
                          type="button"
                        >
                          <Trash2 aria-hidden="true" className="size-4" />
                          Xóa
                        </button>
                      ) : null}
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        ) : null}
        {remove.isError ? (
          <p className="mt-4 text-sm font-semibold text-red-800" role="alert">
            Chưa thể xóa bài viết. Vui lòng thử lại.
          </p>
        ) : null}
        {totalPages > 1 ? (
          <nav
            aria-label="Phân trang bài viết của tôi"
            className="mt-7 flex items-center justify-between gap-4"
          >
            {page > 1 ? (
              <Link
                className="inline-flex min-h-11 items-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                href={pageHref(status, page - 1)}
              >
                Bài trước
              </Link>
            ) : (
              <span />
            )}
            <span
              aria-live="polite"
              className="text-sm text-[var(--theme-muted)]"
            >
              Trang {page} / {totalPages}
            </span>
            {page < totalPages ? (
              <Link
                className="inline-flex min-h-11 items-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                href={pageHref(status, page + 1)}
              >
                Bài tiếp
              </Link>
            ) : (
              <span />
            )}
          </nav>
        ) : null}
      </div>
    </main>
  );
}

function statusLabel(status: CommunityOwnerPostStatus): string {
  switch (status) {
    case "DRAFT":
      return "Bản nháp";
    case "PENDING":
      return "Chờ xử lý (bài viết cũ)";
    case "REJECTED":
      return "Cần chỉnh sửa";
    case "PUBLISHED":
      return "Đã đăng";
    case "HIDDEN":
      return "Đã gỡ bởi quản trị viên";
  }
}

function pageHref(
  status: CommunityOwnerPostStatus | undefined,
  page: number,
): string {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("page", String(page));
  return `/community/mine?${params.toString()}`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(date);
}
