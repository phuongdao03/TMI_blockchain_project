"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, RotateCcw, Send } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { CommunityReportAction } from "@/components/community/community-report-action";
import {
  CommunityMembershipBadge,
} from "@/components/community/community-user-identity";
import { MembershipAvatar } from "@/components/ui/membership-avatar";
import { communityApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import type {
  CommunityCommentCreateResult,
  CommunityCommentFields,
  CommunityCommentInput,
  CommunityCommentReply,
  CommunityCommentSort,
  CommunityCommentThread,
  CommunityPageResponse,
} from "@/lib/api/types";

const PAGE_SIZE = 20;

export function CommunityCommentThreads({
  postId,
  commentCount: initialCommentCount,
}: {
  postId: string;
  commentCount: number;
}) {
  const user = useAuthUser();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [commentCount, setCommentCount] = useState(initialCommentCount);
  const [commentDraft, setCommentDraft] = useState("");
  const [replyDraft, setReplyDraft] = useState("");
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [sort, setSort] = useState<CommunityCommentSort>("oldest");
  const commentsKey = ["community", "comments", postId, page, sort] as const;
  const comments = useQuery({
    queryKey: commentsKey,
    queryFn: ({ signal }) => communityApi.comments(postId, page, signal, sort),
    staleTime: 30_000,
  });
  const createComment = useMutation({
    mutationFn: (input: CommunityCommentInput) =>
      communityApi.createComment(postId, input),
    onSuccess: (created, input) => {
      addCreatedComment(
        queryClient,
        commentsKey,
        created,
        input.parentId,
        sort,
      );
      setCommentCount((count) => count + 1);
      if (input.parentId) {
        setReplyDraft("");
        setReplyingTo(null);
      } else {
        setCommentDraft("");
      }
    },
  });
  const editComment = useMutation({
    mutationFn: ({
      commentId,
      content,
    }: {
      commentId: string;
      content: string;
    }) => communityApi.updateComment(commentId, { content }),
    onSuccess: (updated) => replaceComment(queryClient, commentsKey, updated),
  });
  const deleteComment = useMutation({
    mutationFn: (commentId: string) => communityApi.deleteComment(commentId),
    onSuccess: (_result, commentId) =>
      updateCachedComment(queryClient, commentsKey, commentId, (comment) => ({
        ...comment,
        content: "Bình luận đã bị xóa.",
        author: null,
        isDeleted: true,
        likeCount: 0,
        viewerHasLiked: false,
      })),
  });
  const toggleCommentLike = useMutation({
    mutationFn: ({
      commentId,
      liked,
    }: {
      commentId: string;
      liked: boolean;
    }) =>
      liked
        ? communityApi.unlikeComment(commentId)
        : communityApi.likeComment(commentId),
    onSuccess: (result) => {
      queryClient.setQueriesData<
        CommunityPageResponse<CommunityCommentThread[]>
      >({ queryKey: ["community", "comments", postId] }, (current) =>
        current
          ? {
              ...current,
              data: current.data.map((thread) =>
                updateCommentLike(
                  thread,
                  result.commentId,
                  result.likeCount,
                  result.isLiked,
                ),
              ),
            }
          : current,
      );
    },
  });
  const threads = comments.data?.data ?? [];
  const totalPages = Math.max(
    1,
    Math.ceil(
      (comments.data?.meta.total ?? 0) /
        (comments.data?.meta.pageSize || PAGE_SIZE),
    ),
  );

  function submitComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = commentDraft.trim();
    if (!content || createComment.isPending) return;
    createComment.mutate({ content });
  }

  function submitReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = replyDraft.trim();
    if (!content || !replyingTo || createComment.isPending) return;
    createComment.mutate({ content, parentId: replyingTo });
  }

  return (
    <section
      aria-busy={comments.isPending}
      aria-labelledby="community-comments-title"
      className="mt-7 border-t border-[var(--theme-border)] pt-5 sm:mt-12 sm:pt-9"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2
          id="community-comments-title"
          className="text-xl font-bold text-[var(--theme-text)] sm:text-2xl"
        >
          Thảo luận
        </h2>
        <p aria-live="polite" className="text-sm text-[var(--theme-muted)]">
          {commentCount} bình luận
        </p>
      </header>
      <label className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-[var(--theme-muted)]">
        Sắp xếp bình luận
        <select
          className="min-h-10 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          onChange={(event) => {
            setSort(event.target.value as CommunityCommentSort);
            setPage(1);
          }}
          value={sort}
        >
          <option value="oldest">Cũ nhất</option>
          <option value="newest">Mới nhất</option>
        </select>
      </label>

      {user ? (
        <form
          className="mt-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 sm:mt-5 sm:p-5"
          onSubmit={submitComment}
        >
          <label
            className="block text-sm font-semibold text-[var(--theme-text)]"
            htmlFor="community-comment-draft"
          >
            Bình luận của bạn
          </label>
          <textarea
            aria-describedby="community-comment-help"
            className={inputClass}
            id="community-comment-draft"
            onChange={(event) => setCommentDraft(event.target.value)}
            placeholder="Chia sẻ suy nghĩ của bạn…"
            required
            value={commentDraft}
          />
          <p
            id="community-comment-help"
            className="mt-2 text-xs leading-5 text-[var(--theme-muted)]"
          >
            Hãy trao đổi lịch sự. Nội dung bình luận là văn bản thuần, không
            nhập HTML.
          </p>
          <div className="mt-3 flex justify-end">
            <button
              className={submitClass}
              disabled={!commentDraft.trim() || createComment.isPending}
              type="submit"
            >
              {createComment.isPending ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="size-4 animate-spin"
                />
              ) : (
                <Send aria-hidden="true" className="size-4" />
              )}
              Gửi bình luận
            </button>
          </div>
        </form>
      ) : (
        <p className="mt-5 rounded-xl border border-[var(--theme-border)] p-4 text-sm text-[var(--theme-muted)]">
          Đăng nhập để viết bình luận hoặc trả lời.
        </p>
      )}

      {createComment.isError ? (
        <p
          className="mt-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm font-semibold text-red-900"
          role="alert"
        >
          Chưa thể gửi bình luận. Vui lòng kiểm tra nội dung hoặc kết nối rồi
          thử lại.
        </p>
      ) : null}
      {comments.isPending ? <CommentSkeleton /> : null}
      {comments.isError ? (
        <div
          className="mt-5 rounded-xl border border-[var(--theme-border)] p-5"
          role="alert"
        >
          <p className="text-sm font-semibold text-[var(--theme-text)]">
            Chưa thể tải thảo luận.
          </p>
          <button
            className={`${secondaryClass} mt-3`}
            onClick={() => void comments.refetch()}
            type="button"
          >
            <RotateCcw aria-hidden="true" className="size-4" /> Thử tải lại
          </button>
        </div>
      ) : null}
      {comments.data && threads.length === 0 ? (
        <p className="mt-5 rounded-xl border border-dashed border-[var(--theme-border)] px-5 py-8 text-center text-sm text-[var(--theme-muted)]">
          Chưa có bình luận nào. Hãy bắt đầu cuộc trò chuyện.
        </p>
      ) : null}
      {threads.length > 0 ? (
        <div className="mt-4 space-y-3 sm:mt-5 sm:space-y-4">
          {threads.map((thread) => (
            <CommentThread
              key={thread.id}
              onReply={(commentId) => {
                setReplyingTo((current) =>
                  current === commentId ? null : commentId,
                );
                setReplyDraft("");
              }}
              onReplyDraftChange={setReplyDraft}
              onDeleteComment={(commentId) =>
                deleteComment.mutateAsync(commentId)
              }
              onToggleLike={(commentId, liked) =>
                toggleCommentLike.mutateAsync({ commentId, liked })
              }
              onUpdateComment={(commentId, content) =>
                editComment
                  .mutateAsync({ commentId, content })
                  .then(() => undefined)
              }
              onSubmitReply={submitReply}
              replyDraft={replyDraft}
              replyingTo={replyingTo}
              thread={thread}
              userId={user?.id}
              liking={toggleCommentLike.isPending}
              submitting={createComment.isPending}
              canReply={Boolean(user)}
            />
          ))}
        </div>
      ) : null}
      {totalPages > 1 ? (
        <nav
          aria-label="Phân trang bình luận"
          className="mt-5 flex items-center justify-between gap-3 border-t border-[var(--theme-border)] py-4"
        >
          <button
            className={secondaryClass}
            disabled={page <= 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            type="button"
          >
            Trang trước
          </button>
          <p aria-live="polite" className="text-sm text-[var(--theme-muted)]">
            Trang {page} / {totalPages}
          </p>
          <button
            className={secondaryClass}
            disabled={page >= totalPages}
            onClick={() =>
              setPage((current) => Math.min(totalPages, current + 1))
            }
            type="button"
          >
            Trang sau
          </button>
        </nav>
      ) : null}
    </section>
  );
}

function CommentThread({
  canReply,
  onReply,
  onReplyDraftChange,
  onDeleteComment,
  onToggleLike,
  onUpdateComment,
  onSubmitReply,
  replyDraft,
  replyingTo,
  submitting,
  thread,
  userId,
  liking,
}: {
  canReply: boolean;
  onReply: (commentId: string) => void;
  onReplyDraftChange: (value: string) => void;
  onDeleteComment: (commentId: string) => Promise<void>;
  onToggleLike: (commentId: string, liked: boolean) => Promise<unknown>;
  onUpdateComment: (commentId: string, content: string) => Promise<void>;
  onSubmitReply: (event: FormEvent<HTMLFormElement>) => void;
  replyDraft: string;
  replyingTo: string | null;
  submitting: boolean;
  thread: CommunityCommentThread;
  userId?: string;
  liking: boolean;
}) {
  const authorName = thread.isDeleted
    ? "đã xóa"
    : thread.author?.displayName?.trim() || "Thành viên";
  return (
    <article
      aria-label={`Bình luận của ${authorName}`}
      className="scroll-mt-28 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3.5 sm:p-5"
      id={`comment-${thread.id}`}
    >
      <CommentBody
        author={thread.author}
        commentId={thread.id}
        content={thread.content}
        createdAt={thread.createdAt}
        isDeleted={thread.isDeleted}
        onDelete={onDeleteComment}
        onToggleLike={onToggleLike}
        onUpdate={onUpdateComment}
        userId={userId}
        liking={liking}
        viewerHasLiked={thread.viewerHasLiked}
        likeCount={thread.likeCount}
      />
      {thread.replies.length ? (
        <div className="ml-2 mt-3 space-y-3 border-l border-[var(--theme-border)] pl-3 sm:ml-6 sm:mt-4 sm:pl-4">
          {thread.replies.map((reply) => {
            const parent =
              reply.parentId === thread.id
                ? thread
                : thread.replies.find(
                    (candidate) => candidate.id === reply.parentId,
                  );
            const replyTargetName =
              parent?.author?.displayName?.trim() || "thành viên";
            const replyAuthorName =
              reply.author?.displayName?.trim() || "thành viên";
            return (
              <div
                className="scroll-mt-28 rounded-xl bg-[var(--theme-elevated)] p-3 sm:p-4"
                id={`comment-${reply.id}`}
                key={reply.id}
              >
                {reply.parentId !== thread.id ? (
                  <p className="mb-1 text-xs text-[var(--theme-muted)]">
                    Trả lời {replyTargetName}
                  </p>
                ) : null}
                <CommentBody
                  author={reply.author}
                  commentId={reply.id}
                  content={reply.content}
                  createdAt={reply.createdAt}
                  isDeleted={reply.isDeleted}
                  onDelete={onDeleteComment}
                  onToggleLike={onToggleLike}
                  onUpdate={onUpdateComment}
                  userId={userId}
                  liking={liking}
                  viewerHasLiked={reply.viewerHasLiked}
                  likeCount={reply.likeCount}
                />
                {canReply ? (
                  <button
                    aria-label={`Trả lời ${replyAuthorName}`}
                    className="mt-2 inline-flex min-h-9 items-center rounded-lg px-3 text-sm font-semibold text-[var(--theme-accent)] hover:bg-[var(--theme-surface)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                    onClick={() => onReply(reply.id)}
                    type="button"
                  >
                    Trả lời
                  </button>
                ) : null}
                {replyingTo === reply.id ? (
                  <ReplyComposer
                    commentId={reply.id}
                    onDraftChange={onReplyDraftChange}
                    onSubmit={onSubmitReply}
                    draft={replyDraft}
                    submitting={submitting}
                    targetName={replyAuthorName}
                  />
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
      {canReply ? (
        <button
          aria-label={`Trả lời ${authorName}`}
          className="mt-2 inline-flex min-h-9 items-center rounded-lg px-3 text-sm font-semibold text-[var(--theme-accent)] hover:bg-[var(--theme-elevated)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          onClick={() => onReply(thread.id)}
          type="button"
        >
          Trả lời
        </button>
      ) : null}
      {replyingTo === thread.id ? (
        <ReplyComposer
          commentId={thread.id}
          onDraftChange={onReplyDraftChange}
          onSubmit={onSubmitReply}
          draft={replyDraft}
          submitting={submitting}
          targetName={authorName}
        />
      ) : null}
    </article>
  );
}

function ReplyComposer({
  commentId,
  onDraftChange,
  onSubmit,
  draft,
  submitting,
  targetName,
}: {
  commentId: string;
  onDraftChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  draft: string;
  submitting: boolean;
  targetName: string;
}) {
  return (
    <form
      className="ml-2 mt-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 sm:ml-6 sm:p-4"
      onSubmit={onSubmit}
    >
      <p className="mb-2 text-xs text-[var(--theme-muted)]">
        Trả lời {targetName}
      </p>
      <label
        className="block text-sm font-semibold text-[var(--theme-text)]"
        htmlFor={`community-reply-${commentId}`}
      >
        Nội dung trả lời
      </label>
      <textarea
        className={inputClass}
        id={`community-reply-${commentId}`}
        onChange={(event) => onDraftChange(event.target.value)}
        required
        value={draft}
      />
      <div className="mt-3 flex justify-end">
        <button
          className={submitClass}
          disabled={!draft.trim() || submitting}
          type="submit"
        >
          <Send aria-hidden="true" className="size-4" /> Gửi trả lời
        </button>
      </div>
    </form>
  );
}

function CommentBody({
  author,
  commentId,
  content,
  createdAt,
  isDeleted,
  onDelete,
  onToggleLike,
  onUpdate,
  userId,
  liking,
  likeCount,
  viewerHasLiked,
}: {
  author: CommunityCommentFields["author"];
  commentId: string;
  content: string;
  createdAt: string;
  isDeleted: boolean;
  onDelete: (commentId: string) => Promise<void>;
  onToggleLike: (commentId: string, liked: boolean) => Promise<unknown>;
  onUpdate: (commentId: string, content: string) => Promise<void>;
  userId?: string;
  liking: boolean;
  likeCount: number;
  viewerHasLiked: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(content);
  const [actionError, setActionError] = useState(false);
  const ownsComment = Boolean(userId && author?.id === userId && !isDeleted);
  const name = author?.displayName?.trim() || "Thành viên";

  async function saveEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextContent = draft.trim();
    if (!nextContent) return;
    setActionError(false);
    try {
      await onUpdate(commentId, nextContent);
      setEditing(false);
    } catch {
      setActionError(true);
    }
  }

  async function deleteOwnedComment() {
    setActionError(false);
    try {
      await onDelete(commentId);
    } catch {
      setActionError(true);
    }
  }

  return (
    <div>
      <div className="flex min-w-0 items-center gap-2.5">
        {author ? (
          <>
            <MembershipAvatar
              className="shrink-0"
              displayName={author.displayName}
              size={36}
              src={author.avatarUrl}
              tier={author.membershipTier ?? "MEMBER"}
            />
            <div className="min-w-0">
              <div className="flex max-w-full flex-wrap items-center gap-1.5">
                <Link
                  className="max-w-full truncate text-sm font-bold text-[var(--theme-text)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                  href={`/community/members/${encodeURIComponent(author.username)}`}
                >
                  {name}
                </Link>
                <CommunityMembershipBadge
                  tier={author.membershipTier ?? "MEMBER"}
                />
              </div>
              <time
                className="mt-0.5 block text-xs text-[var(--theme-muted)]"
                dateTime={createdAt}
              >
                {formatDate(createdAt)}
              </time>
            </div>
          </>
        ) : (
          <span className="text-sm font-semibold text-[var(--theme-muted)]">
            {isDeleted ? "Bình luận đã xóa" : "Thành viên"}
          </span>
        )}
      </div>
      {editing ? (
        <form
          className="mt-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 sm:p-4"
          onSubmit={saveEdit}
        >
          <label
            className="block text-sm font-semibold text-[var(--theme-text)]"
            htmlFor={`community-comment-edit-${commentId}`}
          >
            Chỉnh sửa bình luận
          </label>
          <textarea
            className={inputClass}
            id={`community-comment-edit-${commentId}`}
            onChange={(event) => setDraft(event.target.value)}
            required
            value={draft}
          />
          <div className="mt-3 flex flex-wrap justify-end gap-2">
            <button
              className={secondaryClass}
              onClick={() => {
                setDraft(content);
                setEditing(false);
              }}
              type="button"
            >
              Hủy chỉnh sửa
            </button>
            <button
              className={submitClass}
              disabled={!draft.trim()}
              type="submit"
            >
              Lưu chỉnh sửa
            </button>
          </div>
        </form>
      ) : (
        <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-[var(--theme-text)] sm:text-[0.9375rem] sm:leading-7">
          {content}
        </p>
      )}
      {ownsComment ? (
        <div className="mt-1 flex flex-wrap gap-1.5 sm:gap-2">
          <button
            aria-label="Chỉnh sửa bình luận"
            className={commentActionClass}
            onClick={() => {
              setDraft(content);
              setEditing(true);
            }}
            type="button"
          >
            Chỉnh sửa
          </button>
          <button
            aria-label="Xóa bình luận"
            className={commentActionClass}
            onClick={() => void deleteOwnedComment()}
            type="button"
          >
            Xóa
          </button>
        </div>
      ) : null}
      {!isDeleted ? (
        <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-[var(--theme-border)] pt-2">
          {userId ? (
            <button
              aria-pressed={viewerHasLiked}
              className={commentActionClass}
              disabled={liking}
              onClick={() => void onToggleLike(commentId, viewerHasLiked)}
              type="button"
            >
              {viewerHasLiked ? "Bỏ thích" : "Thích"} bình luận ({likeCount})
            </button>
          ) : (
            <span className="text-xs text-[var(--theme-muted)]">
              {likeCount} lượt thích
            </span>
          )}
          <CommunityReportAction
            targetId={commentId}
            targetLabel={`Bình luận của ${name}`}
            targetType="COMMENT"
          />
        </div>
      ) : null}
      {actionError ? (
        <p className="mt-2 text-sm font-semibold text-red-700" role="alert">
          Chưa thể cập nhật bình luận. Vui lòng thử lại.
        </p>
      ) : null}
    </div>
  );
}

function addCreatedComment(
  queryClient: ReturnType<typeof useQueryClient>,
  queryKey: readonly [
    "community",
    "comments",
    string,
    number,
    CommunityCommentSort,
  ],
  created: CommunityCommentCreateResult,
  parentId?: string,
  sort: CommunityCommentSort = "oldest",
) {
  queryClient.setQueryData<CommunityPageResponse<CommunityCommentThread[]>>(
    queryKey,
    (current) => {
      if (!current) return current;
      if (parentId) {
        const reply: CommunityCommentReply = { ...created, parentId };
        return {
          ...current,
          data: current.data.map((thread) =>
            thread.id === parentId ||
            thread.replies.some((item) => item.id === parentId)
              ? {
                  ...thread,
                  replies:
                    sort === "newest"
                      ? [reply, ...thread.replies]
                      : [...thread.replies, reply],
                }
              : thread,
          ),
        };
      }
      const thread: CommunityCommentThread = {
        ...created,
        parentId: null,
        replies: [],
      };
      return {
        ...current,
        data:
          sort === "newest"
            ? [thread, ...current.data]
            : [...current.data, thread],
        meta: { ...current.meta, total: current.meta.total + 1 },
      };
    },
  );
}

function replaceComment(
  queryClient: ReturnType<typeof useQueryClient>,
  queryKey: readonly [
    "community",
    "comments",
    string,
    number,
    CommunityCommentSort,
  ],
  updated: CommunityCommentCreateResult,
) {
  updateCachedComment(queryClient, queryKey, updated.id, (current) => {
    return {
      ...current,
      id: updated.id,
      content: updated.content,
      author: updated.author,
      isDeleted: updated.isDeleted,
      createdAt: updated.createdAt,
    };
  });
}

function updateCachedComment(
  queryClient: ReturnType<typeof useQueryClient>,
  queryKey: readonly [
    "community",
    "comments",
    string,
    number,
    CommunityCommentSort,
  ],
  commentId: string,
  update: (comment: CommunityCommentFields) => CommunityCommentFields,
) {
  queryClient.setQueryData<CommunityPageResponse<CommunityCommentThread[]>>(
    queryKey,
    (current) =>
      current
        ? {
            ...current,
            data: current.data.map((thread) => {
              if (thread.id === commentId) {
                return {
                  ...update(thread),
                  parentId: null,
                  replies: thread.replies,
                };
              }
              return {
                ...thread,
                replies: thread.replies.map((reply) =>
                  reply.id === commentId
                    ? { ...update(reply), parentId: reply.parentId }
                    : reply,
                ),
              };
            }),
          }
        : current,
  );
}

function updateCommentLike(
  thread: CommunityCommentThread,
  commentId: string,
  likeCount: number,
  viewerHasLiked: boolean,
): CommunityCommentThread {
  if (thread.id === commentId) return { ...thread, likeCount, viewerHasLiked };
  return {
    ...thread,
    replies: thread.replies.map((reply) =>
      reply.id === commentId ? { ...reply, likeCount, viewerHasLiked } : reply,
    ),
  };
}

function CommentSkeleton() {
  return (
    <div
      aria-label="Đang tải bình luận"
      className="mt-5 space-y-4"
      role="status"
    >
      {Array.from({ length: 2 }, (_, index) => (
        <div
          aria-hidden="true"
          className="animate-pulse border-b border-[var(--theme-border)] py-5"
          key={index}
        >
          <div className="h-4 w-28 rounded bg-[var(--theme-elevated)]" />
          <div className="mt-3 h-4 w-4/5 rounded bg-[var(--theme-elevated)]" />
        </div>
      ))}
    </div>
  );
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(date);
}

const inputClass =
  "mt-2 min-h-24 w-full resize-y rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 text-sm leading-6 text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20";
const submitClass =
  "inline-flex min-h-10 items-center gap-2 rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50";
const secondaryClass =
  "inline-flex min-h-10 items-center gap-2 rounded-lg border border-[var(--theme-border)] px-3 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50";
const commentActionClass =
  "inline-flex min-h-9 items-center rounded-md px-2 text-xs font-semibold text-[var(--theme-muted)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]";
