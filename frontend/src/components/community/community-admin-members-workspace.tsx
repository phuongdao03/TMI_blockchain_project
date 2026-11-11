"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, Search } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { UserAvatar } from "@/components/ui/user-avatar";
import { communityAdminApi } from "@/lib/api/client";
import type {
  CommunityAdminMember,
  CommunityMemberRestriction,
  CommunityRestrictionScope,
} from "@/lib/api/community-types";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PAGE_SIZE,
  Pagination,
  cardClass,
  formatDate,
  inputClass,
  primaryButtonClass,
  secondaryButtonClass,
  softBadgeClass,
  statusBadgeClass,
  textareaClass,
} from "./community-admin-workspace-primitives";

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
          Tra cứu tên, email và quản lý giới hạn đăng bài hoặc bình luận.
        </p>
      </header>
      <form
        aria-label="Tìm thành viên cộng đồng"
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={submitSearch}
        role="search"
      >
        <label className="sr-only" htmlFor="admin-community-member-search">
          Tên hiển thị, tên người dùng hoặc email
        </label>
        <input
          className={`${inputClass} mt-0 flex-1`}
          id="admin-community-member-search"
          maxLength={120}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder="Tên hiển thị, tên người dùng hoặc email"
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
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            <UserAvatar
              displayName={identity.displayName || identity.email}
              size={44}
              src={identity.avatarUrl}
            />
            <div className="min-w-0">
              {identity.hasPublicProfile ? (
                <Link
                  className="break-words text-sm font-bold text-[var(--theme-text)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 sm:text-lg"
                  href={`/community/members/${encodeURIComponent(identity.username)}`}
                >
                  {identity.displayName || identity.email || "Thành viên"}
                </Link>
              ) : (
                <span className="break-words text-sm font-bold text-[var(--theme-text)] sm:text-lg">
                  {identity.displayName || identity.email || "Thành viên"}
                </span>
              )}
              {identity.email ? (
                <p className="break-all text-xs text-[var(--theme-muted)] sm:text-sm">
                  {identity.email}
                </p>
              ) : null}
            </div>
          </div>
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
            aria-label={`Hạn chế đang hiệu lực của ${identity.displayName}`}
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
          aria-label={expanded ? "Thu gọn" : "Lịch sử và hạn chế"}
          aria-expanded={expanded}
          className={`${secondaryButtonClass} shrink-0 px-2 text-xs sm:px-3 sm:text-sm`}
          onClick={() => setExpanded((value) => !value)}
          type="button"
        >
          <span className="sm:hidden">{expanded ? "Thu gọn" : "Quản lý"}</span>
          <span className="hidden sm:inline">
            {expanded ? "Thu gọn" : "Lịch sử và hạn chế"}
          </span>
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
          <section aria-label={`Lịch sử hạn chế của ${identity.displayName}`}>
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

function scopeLabel(scope: CommunityRestrictionScope): string {
  return scope === "POSTS" ? "Đăng bài" : "Bình luận";
}
