"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, RotateCcw, Search } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { communityAdminApi } from "@/lib/api/client";
import type {
  CommunityAdminComment,
  CommunityAdminMember,
  CommunityAdminPost,
  CommunityCommentVisibility,
  CommunityMemberRestriction,
  CommunityPostStatus,
  CommunityRestrictionScope,
} from "@/lib/api/types";

const PAGE_SIZE = 20;

type PostAction =
  | "hide"
  | "restore-visibility"
  | "pin"
  | "unpin"
  | "lock"
  | "unlock"
  | "delete"
  | "restore-deleted";

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
              {deleted ? "Đã xóa mềm" : postStatusLabel(post.status)}
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
          {post.excerpt ? (
            <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm leading-6 text-[var(--theme-muted)]">
              {post.excerpt}
            </p>
          ) : null}
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
          {deleted ? (
            post.preDeleteStatus !== null ? (
              <ActionButton
                disabled={pending || !reason.trim()}
                onClick={() => onAction("restore-deleted")}
              >
                Khôi phục bài viết
              </ActionButton>
            ) : null
          ) : (
            <ActionButton
              danger
              disabled={pending || !reason.trim()}
              onClick={() => onAction("delete")}
            >
              Xóa mềm
            </ActionButton>
          )}
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
    case "restore-deleted":
      return communityAdminApi.restoreWorkspacePost(post.id, input);
  }
}

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

export function CommunityAdminMembersWorkspace() {
  const [searchDraft, setSearchDraft] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const members = useQuery({
    queryKey: ["admin", "community", "members", { query, page }],
    queryFn: ({ signal }) =>
      communityAdminApi.members(
        { q: query, page, pageSize: PAGE_SIZE },
        signal,
      ),
    staleTime: 15_000,
  });
  const totalPages = Math.max(
    1,
    Math.ceil(
      (members.data?.meta.total ?? 0) /
        (members.data?.meta.pageSize || PAGE_SIZE),
    ),
  );

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setQuery(searchDraft.trim());
    setPage(1);
  }

  return (
    <section
      aria-labelledby="admin-community-members-title"
      aria-busy={members.isPending}
    >
      <header className="mb-4">
        <h2
          className="text-2xl font-bold text-[var(--theme-text)]"
          id="admin-community-members-title"
        >
          Quản lý thành viên
        </h2>
        <p className="mt-1 text-sm text-[var(--theme-muted)]">
          Tra cứu danh tính cộng đồng và quản lý giới hạn đăng bài hoặc bình
          luận. Không hiển thị dữ liệu tài khoản riêng tư.
        </p>
      </header>
      <form
        aria-label="Tìm thành viên cộng đồng"
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={submitSearch}
        role="search"
      >
        <label className="sr-only" htmlFor="admin-community-member-search">
          Tên hiển thị hoặc tên người dùng
        </label>
        <input
          className={`${inputClass} mt-0 flex-1`}
          id="admin-community-member-search"
          maxLength={120}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder="Tên hiển thị hoặc tên người dùng"
          value={searchDraft}
        />
        <button className={primaryButtonClass} type="submit">
          <Search aria-hidden="true" className="size-4" />
          Tìm thành viên
        </button>
      </form>
      {members.isPending ? <LoadingState label="Đang tìm thành viên" /> : null}
      {members.isError ? (
        <ErrorState
          message="Chưa thể tải danh sách thành viên."
          onRetry={() => void members.refetch()}
        />
      ) : null}
      {members.data?.data.length === 0 ? (
        <EmptyState message="Không tìm thấy thành viên phù hợp." />
      ) : null}
      {members.data?.data.length ? (
        <ol className="mt-4 space-y-4">
          {members.data.data.map((member) => (
            <AdminMemberRow key={member.member.id} member={member} />
          ))}
        </ol>
      ) : null}
      {members.data && totalPages > 1 ? (
        <Pagination
          page={page}
          totalPages={totalPages}
          label="Phân trang thành viên quản trị"
          onPageChange={setPage}
        />
      ) : null}
    </section>
  );
}

function AdminMemberRow({ member }: { member: CommunityAdminMember }) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [historyPage, setHistoryPage] = useState(1);
  const [scope, setScope] = useState<CommunityRestrictionScope>("POSTS");
  const [durationMinutes, setDurationMinutes] = useState("60");
  const [reason, setReason] = useState("");
  const [revokeReasons, setRevokeReasons] = useState<Record<string, string>>(
    {},
  );
  const identity = member.member;
  const history = useQuery({
    queryKey: [
      "admin",
      "community",
      "members",
      identity.id,
      "restrictions",
      historyPage,
    ],
    queryFn: ({ signal }) =>
      communityAdminApi.memberRestrictions(identity.id, historyPage, signal),
    enabled: expanded,
    staleTime: 15_000,
  });
  const historyTotalPages = Math.max(
    1,
    Math.ceil(
      (history.data?.meta.total ?? 0) /
        (history.data?.meta.pageSize || PAGE_SIZE),
    ),
  );
  const restrictionQueryKey = ["admin", "community", "members"] as const;
  const createRestriction = useMutation({
    mutationFn: () =>
      communityAdminApi.createMemberRestriction(identity.id, {
        scope,
        durationMinutes: Number(durationMinutes),
        reason: reason.trim(),
      }),
    onSuccess: async () => {
      setReason("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: restrictionQueryKey }),
        queryClient.invalidateQueries({
          queryKey: [
            "admin",
            "community",
            "members",
            identity.id,
            "restrictions",
          ],
        }),
      ]);
    },
  });
  const revokeRestriction = useMutation({
    mutationFn: ({
      restrictionId,
      reason: auditReason,
    }: {
      restrictionId: string;
      reason: string;
    }) =>
      communityAdminApi.revokeMemberRestriction(identity.id, restrictionId, {
        reason: auditReason,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: restrictionQueryKey }),
        queryClient.invalidateQueries({
          queryKey: [
            "admin",
            "community",
            "members",
            identity.id,
            "restrictions",
          ],
        }),
      ]);
    },
  });

  function submitRestriction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !reason.trim() ||
      !Number.isInteger(Number(durationMinutes)) ||
      Number(durationMinutes) < 1 ||
      Number(durationMinutes) > 525_600
    )
      return;
    createRestriction.mutate();
  }

  return (
    <li className={cardClass}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <Link
            className="break-words text-lg font-bold text-[var(--theme-text)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2"
            href={`/community/members/${encodeURIComponent(identity.username)}`}
          >
            {identity.displayName || "Thành viên"}
          </Link>
          <p className="mt-1 text-sm text-[var(--theme-muted)]">
            @{identity.username}
          </p>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-[var(--theme-muted)] sm:grid-cols-4">
            <div>
              <dt>Bài đã đăng</dt>
              <dd className="mt-0.5 font-semibold text-[var(--theme-text)]">
                {member.publishedPostCount}
              </dd>
            </div>
            <div>
              <dt>Bình luận</dt>
              <dd className="mt-0.5 font-semibold text-[var(--theme-text)]">
                {member.commentCount}
              </dd>
            </div>
            <div>
              <dt>Người theo dõi</dt>
              <dd className="mt-0.5 font-semibold text-[var(--theme-text)]">
                {member.followerCount}
              </dd>
            </div>
            <div>
              <dt>Đang theo dõi</dt>
              <dd className="mt-0.5 font-semibold text-[var(--theme-text)]">
                {member.followingCount}
              </dd>
            </div>
          </dl>
          <p className="mt-2 text-xs text-[var(--theme-muted)]">
            Hoạt động gần nhất:{" "}
            {member.lastActivityAt
              ? formatDate(member.lastActivityAt)
              : "Chưa có hoạt động"}
          </p>
          <ul
            aria-label={`Hạn chế đang hiệu lực của ${identity.username}`}
            className="mt-2 flex flex-wrap gap-2"
          >
            {member.activeRestrictions.map((restriction) => (
              <li className={softBadgeClass} key={restriction.id}>
                {scopeLabel(restriction.scope)} đến{" "}
                {formatDate(restriction.expiresAt)}
              </li>
            ))}
          </ul>
        </div>
        <button
          aria-expanded={expanded}
          className={secondaryButtonClass}
          onClick={() => setExpanded((value) => !value)}
          type="button"
        >
          {expanded ? "Thu gọn" : "Lịch sử và hạn chế"}
        </button>
      </div>
      {expanded ? (
        <div className="mt-5 grid gap-5 border-t border-[var(--theme-border)] pt-4 lg:grid-cols-2">
          <form
            className="rounded-xl border border-[var(--theme-border)] p-4"
            onSubmit={submitRestriction}
          >
            <h4 className="font-bold text-[var(--theme-text)]">
              Áp dụng hạn chế
            </h4>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="text-sm font-semibold text-[var(--theme-text)]">
                Phạm vi
                <select
                  className={inputClass}
                  onChange={(event) =>
                    setScope(event.target.value as CommunityRestrictionScope)
                  }
                  value={scope}
                >
                  <option value="POSTS">Đăng bài</option>
                  <option value="COMMENTS">Bình luận</option>
                </select>
              </label>
              <label className="text-sm font-semibold text-[var(--theme-text)]">
                Thời hạn (phút)
                <input
                  className={inputClass}
                  max={525600}
                  min={1}
                  onChange={(event) => setDurationMinutes(event.target.value)}
                  required
                  type="number"
                  value={durationMinutes}
                />
              </label>
            </div>
            <label className="mt-3 block text-sm font-semibold text-[var(--theme-text)]">
              Lý do
              <textarea
                className={textareaClass}
                maxLength={2000}
                onChange={(event) => setReason(event.target.value)}
                required
                rows={3}
                value={reason}
              />
            </label>
            <button
              className={`${primaryButtonClass} mt-3`}
              disabled={!reason.trim() || createRestriction.isPending}
              type="submit"
            >
              {createRestriction.isPending ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="size-4 animate-spin"
                />
              ) : null}
              Áp dụng hạn chế
            </button>
            {createRestriction.isError ? (
              <p
                className="mt-2 text-sm font-semibold text-red-700"
                role="alert"
              >
                Chua th? Áp dụng hạn chế. Kiểm tra thời hạn và thử lại.
              </p>
            ) : null}
          </form>
          <section aria-label={`Lịch sử hạn chế của ${identity.username}`}>
            <h4 className="font-bold text-[var(--theme-text)]">
              Lịch sử hạn chế
            </h4>
            {history.isPending ? (
              <p
                className="mt-3 text-sm text-[var(--theme-muted)]"
                role="status"
              >
                Đang tải lịch sử…
              </p>
            ) : null}
            {history.isError ? (
              <ErrorState
                message="Chưa thể tải lịch sử hạn chế."
                onRetry={() => void history.refetch()}
              />
            ) : null}
            {history.data?.data.length === 0 ? (
              <p className="mt-3 text-sm text-[var(--theme-muted)]">
                Chưa có lịch sử hạn chế.
              </p>
            ) : null}
            {history.data?.data.length ? (
              <ol className="mt-3 space-y-3">
                {history.data.data.map((item) => (
                  <RestrictionHistoryItem
                    key={item.id}
                    restriction={item}
                    revokeReason={revokeReasons[item.id] ?? ""}
                    onReasonChange={(value) =>
                      setRevokeReasons((current) => ({
                        ...current,
                        [item.id]: value,
                      }))
                    }
                    onRevoke={(auditReason) =>
                      revokeRestriction.mutate({
                        restrictionId: item.id,
                        reason: auditReason,
                      })
                    }
                    pending={
                      revokeRestriction.isPending &&
                      revokeRestriction.variables?.restrictionId === item.id
                    }
                    error={
                      revokeRestriction.isError &&
                      revokeRestriction.variables?.restrictionId === item.id
                    }
                  />
                ))}
              </ol>
            ) : null}
            {history.data && historyTotalPages > 1 ? (
              <Pagination
                page={historyPage}
                totalPages={historyTotalPages}
                label="Phân trang lịch sử hạn chế"
                onPageChange={setHistoryPage}
              />
            ) : null}
          </section>
        </div>
      ) : null}
    </li>
  );
}

function RestrictionHistoryItem({
  restriction,
  revokeReason,
  onReasonChange,
  onRevoke,
  pending,
  error,
}: {
  restriction: CommunityMemberRestriction;
  revokeReason: string;
  onReasonChange: (value: string) => void;
  onRevoke: (reason: string) => void;
  pending: boolean;
  error: boolean;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (restriction.status === "ACTIVE" && revokeReason.trim())
      onRevoke(revokeReason.trim());
  }
  return (
    <li className="rounded-lg border border-[var(--theme-border)] p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className={statusBadgeClass}>
          {scopeLabel(restriction.scope)} ·{" "}
          {restriction.status === "ACTIVE"
            ? "Đang hiệu lực"
            : restriction.status === "EXPIRED"
              ? "Đã hết hạn"
              : "Đã thu hồi"}
        </span>
        <span className="text-xs text-[var(--theme-muted)]">
          {formatDate(restriction.startsAt)} -{" "}
          {formatDate(restriction.expiresAt)}
        </span>
      </div>
      <p className="mt-2 text-[var(--theme-text)]">{restriction.reason}</p>
      <p className="mt-1 text-xs text-[var(--theme-muted)]">
        Thực hiện bởi{" "}
        {restriction.actor.displayName || restriction.actor.username} · Mã yêu
        cầu {restriction.requestId}
      </p>
      {restriction.status === "ACTIVE" ? (
        <form
          className="mt-3 border-t border-[var(--theme-border)] pt-3"
          onSubmit={submit}
        >
          <label className="block text-xs font-semibold text-[var(--theme-text)]">
            Lý do thu hồi
            <textarea
              className={textareaClass}
              maxLength={2000}
              onChange={(event) => onReasonChange(event.target.value)}
              required
              rows={2}
              value={revokeReason}
            />
          </label>
          <button
            className={`${secondaryButtonClass} mt-2`}
            disabled={!revokeReason.trim() || pending}
            type="submit"
          >
            {pending ? "Đang thu hồi…" : "Thu hồi hạn chế"}
          </button>
          {error ? (
            <p className="mt-2 text-sm font-semibold text-red-700" role="alert">
              Chưa thể thu hồi hạn chế.
            </p>
          ) : null}
        </form>
      ) : null}
    </li>
  );
}

function ActionButton({
  children,
  onClick,
  disabled,
  danger = false,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      className={danger ? dangerButtonClass : secondaryButtonClass}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function Pagination({
  page,
  totalPages,
  label,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  label: string;
  onPageChange: (page: number) => void;
}) {
  return (
    <nav
      aria-label={label}
      className="mt-5 flex items-center justify-between gap-3 border-t border-[var(--theme-border)] py-4"
    >
      <button
        className={secondaryButtonClass}
        disabled={page <= 1}
        onClick={() => onPageChange(Math.max(1, page - 1))}
        type="button"
      >
        Trang trước
      </button>
      <p aria-live="polite" className="text-sm text-[var(--theme-muted)]">
        Trang {page} / {totalPages}
      </p>
      <button
        className={secondaryButtonClass}
        disabled={page >= totalPages}
        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        type="button"
      >
        Trang sau
      </button>
    </nav>
  );
}

function LoadingState({ label }: { label: string }) {
  return (
    <p
      aria-busy="true"
      className="mt-5 flex items-center gap-2 text-sm text-[var(--theme-muted)]"
      role="status"
    >
      <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
      {label}.
    </p>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      className="mt-5 rounded-xl border border-red-300 bg-red-50 p-4"
      role="alert"
    >
      <p className="text-sm font-semibold text-red-900">{message}</p>
      <button
        className={`${secondaryButtonClass} mt-3`}
        onClick={onRetry}
        type="button"
      >
        <RotateCcw aria-hidden="true" className="size-4" />
        Thử tải lại
      </button>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <p
      className="mt-5 rounded-xl border border-dashed border-[var(--theme-border)] p-8 text-center text-sm text-[var(--theme-muted)]"
      role="status"
    >
      {message}
    </p>
  );
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

function scopeLabel(scope: CommunityRestrictionScope): string {
  return scope === "POSTS" ? "Đăng bài" : "Bình luận";
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa rõ";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

const postStatuses: CommunityPostStatus[] = [
  "DRAFT",
  "PENDING",
  "PUBLISHED",
  "REJECTED",
  "HIDDEN",
  "DELETED",
];
const inputClass =
  "mt-1 min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 py-2 text-sm font-normal text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20";
const textareaClass =
  "mt-1 w-full resize-y rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 text-sm font-normal leading-6 text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20";
const cardClass =
  "rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5";
const statusBadgeClass =
  "inline-flex rounded-full bg-[var(--theme-accent)]/10 px-2.5 py-1 text-xs font-bold text-[var(--theme-accent)]";
const softBadgeClass =
  "inline-flex rounded-full bg-[var(--theme-elevated)] px-2.5 py-1 text-xs font-semibold text-[var(--theme-muted)]";
const primaryButtonClass =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50";
const secondaryButtonClass =
  "inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--theme-border)] px-3 text-sm font-semibold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50";
const dangerButtonClass =
  "inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-red-300 px-3 text-sm font-semibold text-red-700 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700 disabled:cursor-not-allowed disabled:opacity-50";
