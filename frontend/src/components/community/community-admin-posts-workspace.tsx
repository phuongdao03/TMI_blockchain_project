"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { communityAdminApi } from "@/lib/api/client";
import type {
  CommunityAdminPost,
  CommunityPostStatus,
} from "@/lib/api/community-types";
import {
  ActionButton,
  EmptyState,
  ErrorState,
  LoadingState,
  PAGE_SIZE,
  Pagination,
  cardClass,
  formatDate,
  inputClass,
  primaryButtonClass,
  softBadgeClass,
  statusBadgeClass,
  textareaClass,
} from "./community-admin-workspace-primitives";

type PostAction =
  | "hide"
  | "restore-visibility"
  | "pin"
  | "unpin"
  | "lock"
  | "unlock"
  | "delete";

export function CommunityAdminPostsWorkspace() {
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<CommunityPostStatus | "ALL">("ALL");
  const [page, setPage] = useState(1);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const posts = useQuery({
    queryKey: ["admin", "community", "posts", { query, status, page }],
    queryFn: ({ signal }) =>
      communityAdminApi.workspacePosts(
        {
          q: query,
          status: status === "ALL" ? undefined : status,
          page,
          pageSize: PAGE_SIZE,
        },
        signal,
      ),
    staleTime: 15_000,
  });
  const action = useMutation({
    mutationFn: ({
      post,
      type,
      reason,
    }: {
      post: CommunityAdminPost;
      type: PostAction;
      reason: string;
    }) => runPostAction(post, type, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["admin", "community", "posts"],
      });
      await queryClient.invalidateQueries({ queryKey: ["community"] });
    },
  });
  const totalPages = Math.max(
    1,
    Math.ceil(
      (posts.data?.meta.total ?? 0) / (posts.data?.meta.pageSize || PAGE_SIZE),
    ),
  );

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setQuery(searchDraft.trim());
    setPage(1);
  }

  return (
    <section
      aria-labelledby="admin-community-posts-title"
      aria-busy={posts.isPending}
    >
      <header className="mb-4">
        <h2
          className="text-2xl font-bold text-[var(--theme-text)]"
          id="admin-community-posts-title"
        >
          Quản lý bài viết
        </h2>
        <p className="mt-1 text-sm text-[var(--theme-muted)]">
          Quản lý bài viết đã đăng và xem các bản nháp hoặc bài cũ còn chờ xử
          lý. Mọi thay đổi cần có lý do lưu trong lịch sử.
        </p>
      </header>
      <form
        aria-label="Tìm bài viết cộng đồng"
        className="grid gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:grid-cols-[minmax(0,1fr)_14rem_auto]"
        onSubmit={submitSearch}
        role="search"
      >
        <label className="text-sm font-semibold text-[var(--theme-text)]">
          Từ khóa
          <input
            className={inputClass}
            maxLength={120}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder="Tiêu đề, trích đoạn hoặc nội dung"
            value={searchDraft}
          />
        </label>
        <label className="text-sm font-semibold text-[var(--theme-text)]">
          Trạng thái
          <select
            className={inputClass}
            onChange={(event) => {
              setStatus(event.target.value as CommunityPostStatus | "ALL");
              setPage(1);
            }}
            value={status}
          >
            <option value="ALL">Tất cả</option>
            {postStatuses.map((value) => (
              <option key={value} value={value}>
                {postStatusLabel(value)}
              </option>
            ))}
          </select>
        </label>
        <button className={`${primaryButtonClass} self-end`} type="submit">
          <Search aria-hidden="true" className="size-4" />
          Tìm bài viết
        </button>
      </form>
      {posts.isPending ? (
        <LoadingState label="Đang tải bài viết cần kiểm duyệt" />
      ) : null}
      {posts.isError ? (
        <ErrorState
          message="Chưa thể tải danh sách bài viết."
          onRetry={() => void posts.refetch()}
        />
      ) : null}
      {posts.data?.data.length === 0 ? (
        <EmptyState message="Không tìm thấy bài viết phù hợp." />
      ) : null}
      {posts.data?.data.length ? (
        <ol className="mt-4 space-y-4">
          {posts.data.data.map((post) => (
            <AdminPostRow
              key={post.id}
              post={post}
              reason={reasons[post.id] ?? ""}
              onReasonChange={(value) =>
                setReasons((current) => ({ ...current, [post.id]: value }))
              }
              onAction={(type, reason) =>
                action.mutate({
                  post,
                  type,
                  reason: (reason ?? reasons[post.id] ?? "").trim(),
                })
              }
              pending={
                action.isPending && action.variables?.post.id === post.id
              }
              error={action.isError && action.variables?.post.id === post.id}
            />
          ))}
        </ol>
      ) : null}
      {posts.data && totalPages > 1 ? (
        <Pagination
          page={page}
          totalPages={totalPages}
          label="Phân trang bài viết quản trị"
          onPageChange={setPage}
        />
      ) : null}
    </section>
  );
}

function AdminPostRow({
  post,
  reason,
  onReasonChange,
  onAction,
  pending,
  error,
}: {
  post: CommunityAdminPost;
  reason: string;
  onReasonChange: (value: string) => void;
  onAction: (action: PostAction, reason?: string) => void;
  pending: boolean;
  error: boolean;
}) {
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false);
  const [permanentDeleteDialogOpen, setPermanentDeleteDialogOpen] =
    useState(false);
  const [removalReason, setRemovalReason] = useState("");
  const deleted = post.status === "DELETED" || Boolean(post.deletedAt);
  const ownerDeleted =
    post.status === "DELETED" && post.preDeleteStatus === null;
  const hidden = post.status === "HIDDEN";
  const canPin = post.status === "PUBLISHED" && !deleted && !hidden;
  return (
    <li className={cardClass}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={statusBadgeClass}>
              {deleted ? "Đã xóa" : postStatusLabel(post.status)}
            </span>
            {post.isPinned ? (
              <span className={softBadgeClass}>Đã ghim</span>
            ) : null}
            {post.commentsLocked ? (
              <span className={softBadgeClass}>Đã khóa bình luận</span>
            ) : null}
          </div>
          <h3 className="mt-2 break-words text-lg font-bold text-[var(--theme-text)]">
            {post.title}
          </h3>
          <p className="mt-1 text-sm text-[var(--theme-muted)]">
            {post.category.name} · @{post.author.username} ·{" "}
            {post.author.displayName || "Thành viên"}
          </p>
          <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-[var(--theme-text)]">
            {post.content}
          </p>
          <p className="mt-2 text-xs text-[var(--theme-muted)]">
            {post.viewCount} lượt xem · {post.likeCount} lượt thích ·{" "}
            {post.commentCount} bình luận
          </p>
          {deleted ? (
            <p className="mt-2 text-xs text-[var(--theme-muted)]">
              {post.deletedAt
                ? `Đã xóa lúc ${formatDate(post.deletedAt)}`
                : "Đã xóa"}
              {post.preDeleteStatus
                ? ` · Trạng thái trước đó: ${postStatusLabel(post.preDeleteStatus)}`
                : ownerDeleted
                  ? " · Tác giả đã xóa bài viết"
                  : ""}
            </p>
          ) : null}
          {post.status === "PUBLISHED" && !deleted ? (
            <Link
              className="mt-2 inline-flex min-h-9 items-center text-sm font-semibold text-[var(--theme-accent)] underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2"
              href={`/community/posts/${encodeURIComponent(post.slug)}`}
            >
              Mở bài viết công khai
            </Link>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2 lg:max-w-sm lg:justify-end">
          {hidden ? (
            <ActionButton
              disabled={pending || !reason.trim()}
              onClick={() => onAction("restore-visibility")}
            >
              Khôi phục hiển thị
            </ActionButton>
          ) : !deleted ? (
            <ActionButton
              disabled={pending}
              onClick={() => setRemoveDialogOpen(true)}
            >
              Gỡ bài viết
            </ActionButton>
          ) : null}
          {canPin ? (
            <ActionButton
              disabled={pending || !reason.trim()}
              onClick={() => onAction(post.isPinned ? "unpin" : "pin")}
            >
              {post.isPinned ? "Bỏ ghim" : "Ghim bài viết"}
            </ActionButton>
          ) : null}
          {!deleted ? (
            <ActionButton
              disabled={pending || !reason.trim()}
              onClick={() => onAction(post.commentsLocked ? "unlock" : "lock")}
            >
              {post.commentsLocked ? "Mở khóa bình luận" : "Khóa bình luận"}
            </ActionButton>
          ) : null}
          {!deleted ? (
            <ActionButton
              danger
              disabled={pending || !reason.trim()}
              onClick={() => setPermanentDeleteDialogOpen(true)}
            >
              Xóa vĩnh viễn
            </ActionButton>
          ) : null}
        </div>
      </div>
      <div className="mt-4 border-t border-[var(--theme-border)] pt-3">
        <label className="block text-sm font-semibold text-[var(--theme-text)]">
          Lý do thao tác
          <textarea
            className={textareaClass}
            maxLength={2000}
            onChange={(event) => onReasonChange(event.target.value)}
            required
            rows={2}
            value={reason}
          />
        </label>
        {pending ? (
          <p className="mt-2 text-sm text-[var(--theme-muted)]" role="status">
            Đang xử lý…
          </p>
        ) : null}
        {error ? (
          <p className="mt-2 text-sm font-semibold text-red-700" role="alert">
            Không thể cập nhật bài viết. Vui lòng kiểm tra trạng thái hoặc lý
            do.
          </p>
        ) : null}
      </div>
      {removeDialogOpen ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/55 p-4">
          <section
            aria-labelledby={`remove-post-title-${post.id}`}
            aria-modal="true"
            className="w-full max-w-lg rounded-2xl bg-[var(--theme-surface)] p-5 text-[var(--theme-text)] shadow-2xl sm:p-6"
            role="dialog"
          >
            <h3
              className="text-xl font-bold"
              id={`remove-post-title-${post.id}`}
            >
              Gỡ bài viết
            </h3>
            <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
              Bài viết sẽ không còn hiển thị công khai. Tác giả sẽ nhận được
              thông báo về lý do gỡ bài.
            </p>
            <label className="mt-4 block text-sm font-semibold">
              Gợi ý lý do
              <select
                className={inputClass}
                onChange={(event) => {
                  if (event.target.value) setRemovalReason(event.target.value);
                }}
                value=""
              >
                <option value="">Chọn lý do gợi ý</option>
                <option value="Nội dung không phù hợp.">
                  Nội dung không phù hợp
                </option>
                <option value="Spam hoặc quảng cáo.">
                  Spam hoặc quảng cáo
                </option>
                <option value="Ngôn từ thiếu văn minh.">
                  Ngôn từ thiếu văn minh
                </option>
                <option value="Vi phạm quy định cộng đồng.">
                  Vi phạm quy định cộng đồng
                </option>
                <option value="Nội dung sai lệch hoặc gây hiểu nhầm.">
                  Nội dung sai lệch hoặc gây hiểu nhầm
                </option>
              </select>
            </label>
            <label
              className="mt-3 block text-sm font-semibold"
              htmlFor={`remove-post-reason-${post.id}`}
            >
              Lý do gỡ bài
              <textarea
                className={textareaClass}
                id={`remove-post-reason-${post.id}`}
                maxLength={2000}
                onChange={(event) => setRemovalReason(event.target.value)}
                required
                rows={4}
                value={removalReason}
              />
            </label>
            <div className="mt-5 flex flex-wrap justify-end gap-2">
              <ActionButton
                disabled={pending}
                onClick={() => setRemoveDialogOpen(false)}
              >
                Hủy
              </ActionButton>
              <ActionButton
                danger
                disabled={pending || !removalReason.trim()}
                onClick={() => {
                  onAction("hide", removalReason.trim());
                  setRemoveDialogOpen(false);
                  setRemovalReason("");
                }}
              >
                Gỡ bài viết
              </ActionButton>
            </div>
          </section>
        </div>
      ) : null}
      {permanentDeleteDialogOpen ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/55 p-4">
          <section
            aria-labelledby={`permanent-delete-post-title-${post.id}`}
            aria-modal="true"
            className="w-full max-w-lg rounded-2xl bg-[var(--theme-surface)] p-5 text-[var(--theme-text)] shadow-2xl sm:p-6"
            role="dialog"
          >
            <h3
              className="text-xl font-bold"
              id={`permanent-delete-post-title-${post.id}`}
            >
              Xóa vĩnh viễn bài viết?
            </h3>
            <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
              Bài viết, bình luận, báo cáo, lượt thích và ảnh đính kèm sẽ bị xóa
              vĩnh viễn. Bạn không thể khôi phục dữ liệu này.
            </p>
            <div className="mt-5 flex flex-wrap justify-end gap-2">
              <ActionButton
                disabled={pending}
                onClick={() => setPermanentDeleteDialogOpen(false)}
              >
                Hủy
              </ActionButton>
              <ActionButton
                danger
                disabled={pending || !reason.trim()}
                onClick={() => {
                  onAction("delete", reason.trim());
                  setPermanentDeleteDialogOpen(false);
                }}
              >
                Xóa vĩnh viễn
              </ActionButton>
            </div>
          </section>
        </div>
      ) : null}
    </li>
  );
}

async function runPostAction(
  post: CommunityAdminPost,
  action: PostAction,
  reason: string,
) {
  const input = { reason };
  switch (action) {
    case "hide":
      return communityAdminApi.hidePost(post.id, input);
    case "restore-visibility":
      return communityAdminApi.restorePost(post.id, input);
    case "pin":
      return communityAdminApi.pinPost(post.id, input);
    case "unpin":
      return communityAdminApi.unpinPost(post.id, input);
    case "lock":
      return communityAdminApi.lockPostComments(post.id, input);
    case "unlock":
      return communityAdminApi.unlockPostComments(post.id, input);
    case "delete":
      return communityAdminApi.deleteWorkspacePost(post.id, input);
  }
}

function postStatusLabel(status: CommunityPostStatus): string {
  const labels: Record<CommunityPostStatus, string> = {
    DRAFT: "Bản nháp",
    PENDING: "Chờ xử lý (bài cũ)",
    PUBLISHED: "Đã đăng",
    REJECTED: "Cần chỉnh sửa",
    HIDDEN: "Đã ẩn",
    DELETED: "Đã xóa",
  };
  return labels[status];
}

const postStatuses: CommunityPostStatus[] = [
  "DRAFT",
  "PENDING",
  "PUBLISHED",
  "REJECTED",
  "HIDDEN",
  "DELETED",
];
