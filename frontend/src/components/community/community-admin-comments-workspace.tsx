"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { communityAdminApi } from "@/lib/api/client";
import type {
  CommunityAdminComment,
  CommunityCommentVisibility,
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

export function CommunityAdminCommentsWorkspace() {
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState({
    q: "",
    postId: "",
    authorUsername: "",
  });
  const [filters, setFilters] = useState({
    q: "",
    postId: "",
    authorUsername: "",
    visibility: "ALL" as CommunityCommentVisibility | "ALL",
  });
  const [page, setPage] = useState(1);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const comments = useQuery({
    queryKey: ["admin", "community", "comments", { ...filters, page }],
    queryFn: ({ signal }) =>
      communityAdminApi.workspaceComments(
        { ...filters, page, pageSize: PAGE_SIZE },
        signal,
      ),
    staleTime: 15_000,
  });
  const action = useMutation({
    mutationFn: ({
      comment,
      type,
      reason,
    }: {
      comment: CommunityAdminComment;
      type: "hide" | "restore" | "delete";
      reason: string;
    }) => {
      const input = { reason };
      if (type === "hide")
        return communityAdminApi.hideWorkspaceComment(comment.id, input);
      if (type === "restore")
        return communityAdminApi.restoreWorkspaceComment(comment.id, input);
      return communityAdminApi.deleteWorkspaceComment(comment.id, input);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["admin", "community", "comments"],
      });
    },
  });
  const totalPages = Math.max(
    1,
    Math.ceil(
      (comments.data?.meta.total ?? 0) /
        (comments.data?.meta.pageSize || PAGE_SIZE),
    ),
  );

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters({ ...searchDraft, visibility: filters.visibility });
    setPage(1);
  }

  return (
    <section
      aria-labelledby="admin-community-comments-title"
      aria-busy={comments.isPending}
    >
      <header className="mb-4">
        <h2
          className="text-2xl font-bold text-[var(--theme-text)]"
          id="admin-community-comments-title"
        >
          Quản lý bình luận
        </h2>
        <p className="mt-1 text-sm text-[var(--theme-muted)]">
          Tìm theo nội dung, bài viết hoặc tên thành viên; trạng thái hiển thị
          được giữ nguyên trong luồng trao đổi.
        </p>
      </header>
      <form
        aria-label="Lọc bình luận cộng đồng"
        className="grid gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:grid-cols-2 lg:grid-cols-4"
        onSubmit={submitSearch}
        role="search"
      >
        <label className="text-sm font-semibold text-[var(--theme-text)]">
          Nội dung
          <input
            className={inputClass}
            maxLength={120}
            onChange={(event) =>
              setSearchDraft({ ...searchDraft, q: event.target.value })
            }
            value={searchDraft.q}
          />
        </label>
        <label className="text-sm font-semibold text-[var(--theme-text)]">
          Mã bài viết
          <input
            className={inputClass}
            onChange={(event) =>
              setSearchDraft({ ...searchDraft, postId: event.target.value })
            }
            value={searchDraft.postId}
          />
        </label>
        <label className="text-sm font-semibold text-[var(--theme-text)]">
          Tên người dùng
          <input
            className={inputClass}
            maxLength={30}
            onChange={(event) =>
              setSearchDraft({
                ...searchDraft,
                authorUsername: event.target.value,
              })
            }
            value={searchDraft.authorUsername}
          />
        </label>
        <label className="text-sm font-semibold text-[var(--theme-text)]">
          Hiển thị
          <select
            className={inputClass}
            onChange={(event) => {
              setFilters({
                ...filters,
                visibility: event.target.value as
                  | CommunityCommentVisibility
                  | "ALL",
              });
              setPage(1);
            }}
            value={filters.visibility}
          >
            <option value="ALL">Tất cả</option>
            <option value="VISIBLE">Đang hiển thị</option>
            <option value="HIDDEN">Đã ẩn</option>
            <option value="DELETED">Đã xóa</option>
          </select>
        </label>
        <button
          className={`${primaryButtonClass} sm:col-span-2 lg:col-span-4`}
          type="submit"
        >
          <Search aria-hidden="true" className="size-4" />
          Tìm bình luận
        </button>
      </form>
      {comments.isPending ? <LoadingState label="Đang tải bình luận" /> : null}
      {comments.isError ? (
        <ErrorState
          message="Chưa thể tải danh sách bình luận."
          onRetry={() => void comments.refetch()}
        />
      ) : null}
      {comments.data?.data.length === 0 ? (
        <EmptyState message="Không tìm thấy bình luận phù hợp." />
      ) : null}
      {comments.data?.data.length ? (
        <ol className="mt-4 space-y-4">
          {comments.data.data.map((comment) => (
            <AdminCommentRow
              key={comment.id}
              comment={comment}
              reason={reasons[comment.id] ?? ""}
              pending={
                action.isPending && action.variables?.comment.id === comment.id
              }
              error={
                action.isError && action.variables?.comment.id === comment.id
              }
              onReasonChange={(value) =>
                setReasons((current) => ({ ...current, [comment.id]: value }))
              }
              onAction={(type) =>
                action.mutate({
                  comment,
                  type,
                  reason: (reasons[comment.id] ?? "").trim(),
                })
              }
            />
          ))}
        </ol>
      ) : null}
      {comments.data && totalPages > 1 ? (
        <Pagination
          page={page}
          totalPages={totalPages}
          label="Phân trang bình luận quản trị"
          onPageChange={setPage}
        />
      ) : null}
    </section>
  );
}

function AdminCommentRow({
  comment,
  reason,
  pending,
  error,
  onReasonChange,
  onAction,
}: {
  comment: CommunityAdminComment;
  reason: string;
  pending: boolean;
  error: boolean;
  onReasonChange: (value: string) => void;
  onAction: (action: "hide" | "restore" | "delete") => void;
}) {
  const author = comment.author;
  return (
    <li className={cardClass}>
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={
            comment.visibility === "VISIBLE" ? statusBadgeClass : softBadgeClass
          }
        >
          {comment.visibility === "VISIBLE"
            ? "Đang hiển thị"
            : comment.visibility === "HIDDEN"
              ? "Đã ẩn"
              : "Đã xóa"}
        </span>
        <time
          className="text-xs text-[var(--theme-muted)]"
          dateTime={comment.createdAt}
        >
          {formatDate(comment.createdAt)}
        </time>
      </div>
      <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-[var(--theme-text)]">
        {comment.content}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--theme-muted)]">
        <span>
          {author
            ? `@${author.username} · ${author.displayName || "Thành viên"}`
            : "Tác giả đã ẩn danh"}
        </span>
        <span aria-hidden="true">·</span>
        <Link
          className="font-semibold text-[var(--theme-accent)] underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2"
          href={`/community/posts/${encodeURIComponent(comment.post.slug)}`}
        >
          {comment.post.title}
        </Link>
      </div>
      <div className="mt-4 grid gap-3 border-t border-[var(--theme-border)] pt-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
        <label className="text-sm font-semibold text-[var(--theme-text)]">
          Lý do kiểm duyệt
          <textarea
            className={textareaClass}
            maxLength={2000}
            onChange={(event) => onReasonChange(event.target.value)}
            required
            rows={2}
            value={reason}
          />
        </label>
        <div className="flex flex-wrap gap-2">
          {comment.visibility === "VISIBLE" ? (
            <ActionButton
              disabled={pending || !reason.trim()}
              onClick={() => onAction("hide")}
            >
              Ẩn bình luận
            </ActionButton>
          ) : null}
          {comment.visibility !== "VISIBLE" ? (
            <ActionButton
              disabled={pending || !reason.trim()}
              onClick={() => onAction("restore")}
            >
              Khôi phục bình luận
            </ActionButton>
          ) : null}
          {comment.visibility !== "DELETED" ? (
            <ActionButton
              danger
              disabled={pending || !reason.trim()}
              onClick={() => onAction("delete")}
            >
              Xóa bình luận
            </ActionButton>
          ) : null}
        </div>
        {error ? (
          <p
            className="text-sm font-semibold text-red-700 sm:col-span-2"
            role="alert"
          >
            Không thể cập nhật bình luận. Nếu chủ nhân đã xóa, bình luận không
            thể khôi phục.
          </p>
        ) : null}
      </div>
    </li>
  );
}
