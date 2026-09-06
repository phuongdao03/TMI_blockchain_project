"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  LockKeyhole,
  Search,
  ShieldCheck,
  UserPlus,
  UsersRound,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import {
  ApiError,
  adminUsersApi,
  staffAccountsApi,
  staffInvitationsApi,
} from "@/lib/api/client";
import type { StaffAccountRole, StaffAccountStatus } from "@/lib/api/types";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { SelectControl } from "@/components/ui/form-controls";
import { STAFF_ACCOUNT_ROLES } from "./staff-account-roles";

const inputClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-100";

function invitationErrorMessage(cause: unknown): string {
  if (
    (cause instanceof ApiError && cause.code === "STAFF_ACCOUNT_EXISTS") ||
    (cause instanceof Error && cause.message.includes("already exists"))
  ) {
    return "Tài khoản này đã tồn tại. Hãy chọn tài khoản trong danh sách và cấp nhiệm vụ phù hợp thay vì gửi lời mời mới.";
  }
  if (cause instanceof ApiError) return cause.message;
  return "Không thể gửi lời mời lúc này. Vui lòng thử lại hoặc kiểm tra cấu hình gửi email.";
}

export function StaffAccountWorkspace() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [candidateSearch, setCandidateSearch] = useState("");
  const role: StaffAccountRole = "MODERATOR";
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<StaffAccountStatus | "ALL">("ALL");
  const [roleFilter, setRoleFilter] = useState<StaffAccountRole | "ALL">("ALL");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [confirmInvite, setConfirmInvite] = useState(false);
  const [pendingUpdate, setPendingUpdate] = useState<{
    id: string;
    email: string;
    status?: StaffAccountStatus;
    role?: StaffAccountRole;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const accounts = useQuery({
    queryKey: ["admin", "staff-accounts", query, status, roleFilter],
    queryFn: () =>
      staffAccountsApi.list({
        pageSize: 100,
        query: query || undefined,
        status: status === "ALL" ? undefined : status,
        role: roleFilter === "ALL" ? undefined : roleFilter,
      }),
  });
  const invitations = useQuery({
    queryKey: ["admin", "staff-invitations"],
    queryFn: () => staffInvitationsApi.list(1, 20),
  });
  const candidates = useQuery({
    queryKey: ["admin", "reviewer-candidates", candidateSearch],
    queryFn: () =>
      adminUsersApi.list({
        page: 1,
        pageSize: 100,
        search: candidateSearch || undefined,
        status: "ACTIVE",
        verified: true,
        sortBy: "email",
        sortOrder: "asc",
      }),
  });
  const create = useMutation({
    mutationFn: () => staffInvitationsApi.create({ email, role }),
    onSuccess: () => {
      setEmail("");
      setConfirmInvite(false);
      setFeedback(
        "Đã gửi lời mời bảo mật. Nhân sự cần xác minh đúng email nhận lời mời để kích hoạt tài khoản.",
      );
      setError(null);
      void queryClient.invalidateQueries({
        queryKey: ["admin", "staff-invitations"],
      });
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (cause) => {
      setConfirmInvite(false);
      setError(invitationErrorMessage(cause));
    },
  });
  const invitationAction = useMutation({
    mutationFn: ({
      id,
      action,
    }: {
      id: string;
      action: "resend" | "revoke";
    }) =>
      action === "resend"
        ? staffInvitationsApi.resend(id)
        : staffInvitationsApi.revoke(id),
    onSuccess: (_, variables) => {
      setFeedback(
        variables.action === "resend"
          ? "Đã gửi lại lời mời mới. Liên kết cũ không còn hiệu lực."
          : "Đã thu hồi lời mời.",
      );
      setError(null);
      void queryClient.invalidateQueries({
        queryKey: ["admin", "staff-invitations"],
      });
    },
    onError: (cause) =>
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Không thể cập nhật lời mời lúc này.",
      ),
  });
  const update = useMutation({
    mutationFn: (input: {
      id: string;
      email?: string;
      status: "ACTIVE" | "SUSPENDED" | "DISABLED";
    }) => {
      return staffAccountsApi.update(input.id, {
        status: input.status,
      });
    },
    onSuccess: () => {
      setPendingUpdate(null);
      setFeedback("Đã cập nhật thông tin tài khoản.");
      setError(null);
      void queryClient.invalidateQueries({
        queryKey: ["admin", "staff-accounts"],
      });
    },
    onError: (cause) =>
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Không thể cập nhật tài khoản.",
      ),
  });
  const rows = accounts.data?.data ?? [];
  const activeCount = rows.filter(
    (account) => account.status === "ACTIVE",
  ).length;
  const suspendedCount = rows.filter(
    (account) => account.status === "SUSPENDED",
  ).length;
  const selectedRole = STAFF_ACCOUNT_ROLES.find((item) => item.value === role);
  const pendingEmails = new Set(
    (invitations.data?.data ?? [])
      .filter((invitation) => invitation.status === "PENDING")
      .map((invitation) => invitation.email.toLowerCase()),
  );
  const eligibleUsers = (candidates.data?.data ?? []).filter(
    (user) =>
      !user.roles.includes("SUPER_ADMIN") && !user.roles.includes("MODERATOR"),
  );

  return (
    <div className="staff-account-workspace mx-auto max-w-7xl space-y-7 pb-8">
      <header className="border-b border-neutral-200 pb-6">
        <Link
          className="inline-flex items-center gap-2 text-sm font-bold text-neutral-500 transition hover:text-neutral-950"
          href="/admin"
        >
          <ArrowLeft aria-hidden="true" className="size-4" />
          Trung tâm quản trị
        </Link>
        <div className="mt-6 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
              <UsersRound aria-hidden="true" className="size-4" />
              Đội ngũ làm việc
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl">
              Mời và quản lý người phụ trách
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
              Mời nhân sự bằng email công việc, theo dõi quá trình kích hoạt và
              khóa quyền truy cập ngay khi không còn sử dụng.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-primary-100 bg-primary-50 px-4 py-3 text-sm font-semibold text-primary-700">
            <ShieldCheck aria-hidden="true" className="size-5" />
            Khu vực quản trị
          </div>
        </div>
      </header>
      {feedback ? (
        <p
          className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm leading-6 text-emerald-800"
          role="status"
        >
          <CheckCircle2 aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          {feedback}
        </p>
      ) : null}
      {error ? (
        <p
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-800"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      <section
        aria-label="Tóm tắt tài khoản"
        className="grid gap-3 sm:grid-cols-3"
      >
        <SummaryCard
          label="Tổng tài khoản"
          value={accounts.data?.meta.total ?? rows.length}
          tone="neutral"
        />
        <SummaryCard label="Đang hoạt động" value={activeCount} tone="green" />
        <SummaryCard label="Đã khóa" value={suspendedCount} tone="red" />
      </section>
      <div className="grid gap-6 xl:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.6fr)]">
        <section className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div className="flex items-start gap-3">
            <span className="rounded-xl bg-neutral-950 p-3 text-white">
              <UserPlus aria-hidden="true" className="size-5" />
            </span>
            <div>
              <h2 className="text-lg font-bold text-neutral-950">
                Chọn người kiểm duyệt
              </h2>
              <p className="mt-1 text-sm leading-6 text-neutral-600">
                Chọn một tài khoản đã hoạt động trên hệ thống. Người đó chỉ nhận
                quyền kiểm duyệt sau khi tự chấp nhận lời mời.
              </p>
            </div>
          </div>
          <label
            className="mt-6 block text-sm font-semibold"
            htmlFor="reviewer-search"
          >
            Tìm tài khoản
            <input
              className={inputClass}
              id="reviewer-search"
              onChange={(event) => setCandidateSearch(event.target.value)}
              placeholder="Tên hoặc email"
              type="search"
              value={candidateSearch}
            />
          </label>
          <div
            className="mt-4 max-h-80 space-y-2 overflow-y-auto"
            data-testid="reviewer-candidates"
          >
            {candidates.isPending ? <TableSkeleton /> : null}
            {!candidates.isPending && eligibleUsers.length === 0 ? (
              <p className="rounded-xl border border-dashed border-neutral-300 p-4 text-sm text-neutral-600">
                Không có tài khoản phù hợp. Tài khoản phải đang hoạt động và đã
                xác minh email.
              </p>
            ) : null}
            {eligibleUsers.map((user) => {
              const pending = pendingEmails.has(user.email.toLowerCase());
              return (
                <article
                  className="rounded-xl border border-neutral-200 p-3"
                  key={user.id}
                >
                  <p className="truncate text-sm font-bold text-neutral-950">
                    {user.fullName || user.email}
                  </p>
                  <p className="truncate text-xs text-neutral-500">
                    {user.email}
                  </p>
                  <button
                    className="mt-3 min-h-10 w-full rounded-lg bg-neutral-950 px-3 text-xs font-bold text-white disabled:opacity-50"
                    disabled={pending || create.isPending}
                    onClick={() => {
                      setEmail(user.email);
                      setFeedback(null);
                      setError(null);
                      setConfirmInvite(true);
                    }}
                    type="button"
                  >
                    {pending
                      ? "Đang chờ xác nhận"
                      : "Chọn làm người kiểm duyệt"}
                  </button>
                </article>
              );
            })}
          </div>
          <div className="mt-5 border-t border-neutral-100 pt-4 text-xs leading-5 text-neutral-500">
            Lời mời chỉ dùng một lần và hết hạn sau 24 giờ. Quản trị viên là cấp
            phê duyệt cao nhất; người được chọn vẫn phải tự xác nhận để nhận
            quyền.
          </div>
          <div className="mt-6 border-t border-neutral-200 pt-5">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-bold text-neutral-950">
                Lời mời gần đây
              </h3>
              <span className="text-xs text-neutral-500">
                {invitations.data?.meta.total ?? 0} lời mời
              </span>
            </div>
            <div className="mt-3 space-y-2">
              {(invitations.data?.data ?? []).slice(0, 5).map((invitation) => (
                <article
                  className="rounded-xl border border-neutral-200 p-3"
                  key={invitation.id}
                >
                  <p className="truncate text-sm font-semibold text-neutral-900">
                    {invitation.email}
                  </p>
                  <p className="mt-1 text-xs text-neutral-500">
                    {invitation.status === "PENDING"
                      ? `Chờ xác nhận · hết hạn ${new Date(invitation.expiresAt).toLocaleString("vi-VN")}`
                      : invitation.status === "ACCEPTED"
                        ? "Đã kích hoạt"
                        : invitation.status === "REVOKED"
                          ? "Đã thu hồi"
                          : "Đã hết hạn"}
                  </p>
                  {invitation.status === "PENDING" ? (
                    <div className="mt-3 flex gap-2">
                      <button
                        className="text-xs font-bold text-neutral-700 hover:text-neutral-950"
                        disabled={invitationAction.isPending}
                        onClick={() =>
                          invitationAction.mutate({
                            id: invitation.id,
                            action: "resend",
                          })
                        }
                        type="button"
                      >
                        Gửi lại
                      </button>
                      <button
                        className="text-xs font-bold text-red-700 hover:text-red-900"
                        disabled={invitationAction.isPending}
                        onClick={() =>
                          invitationAction.mutate({
                            id: invitation.id,
                            action: "revoke",
                          })
                        }
                        type="button"
                      >
                        Thu hồi
                      </button>
                    </div>
                  ) : null}
                </article>
              ))}
              {!invitations.isPending &&
              (invitations.data?.data.length ?? 0) === 0 ? (
                <p className="py-3 text-xs leading-5 text-neutral-500">
                  Chưa có lời mời nào.
                </p>
              ) : null}
            </div>
          </div>
        </section>
        <section className="min-w-0 overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
          <div className="border-b border-neutral-200 px-5 py-5 sm:px-6">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <h2 className="text-lg font-bold text-neutral-950">
                  Danh sách tài khoản
                </h2>
                <p className="mt-1 text-sm text-neutral-600">
                  Khóa tài khoản sẽ dừng các phiên đang hoạt động.
                </p>
              </div>
              <span className="text-sm font-semibold text-neutral-500">
                {accounts.data?.meta.total ?? 0} tài khoản
              </span>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-[1fr_10rem_11rem]">
              <label className="relative block">
                <span className="sr-only">Tìm theo email</span>
                <Search
                  aria-hidden="true"
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400"
                />
                <input
                  aria-label="Tìm theo email"
                  className="min-h-11 w-full rounded-xl border border-neutral-300 pl-9 pr-3 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
                  id="staff-search"
                  name="staffSearch"
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Tìm theo email…"
                  type="search"
                  value={query}
                />
              </label>
              <label>
                <span className="sr-only">Lọc trạng thái</span>
                <SelectControl
                  aria-label="Lọc trạng thái"
                  className="min-h-11 w-full rounded-xl border border-neutral-300 px-3 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
                  id="staff-status-filter"
                  name="staffStatusFilter"
                  onChange={(event) =>
                    setStatus(event.target.value as StaffAccountStatus | "ALL")
                  }
                  value={status}
                >
                  <option value="ALL">Tất cả trạng thái</option>
                  <option value="ACTIVE">Đang hoạt động</option>
                  <option value="SUSPENDED">Đã khóa</option>
                  <option value="DISABLED">Đã vô hiệu hóa</option>
                </SelectControl>
              </label>
              <label>
                <span className="sr-only">Lọc nhiệm vụ</span>
                <SelectControl
                  aria-label="Lọc nhiệm vụ"
                  className="min-h-11 w-full rounded-xl border border-neutral-300 px-3 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
                  id="staff-role-filter"
                  name="staffRoleFilter"
                  onChange={(event) =>
                    setRoleFilter(
                      event.target.value as StaffAccountRole | "ALL",
                    )
                  }
                  value={roleFilter}
                >
                  <option value="ALL">Tất cả nhiệm vụ</option>
                  {STAFF_ACCOUNT_ROLES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </SelectControl>
              </label>
            </div>
          </div>
          {accounts.isPending ? <TableSkeleton /> : null}
          {accounts.isError ? (
            <p className="p-6 text-sm text-red-700" role="alert">
              Không thể tải danh sách tài khoản. Vui lòng thử lại hoặc liên hệ
              người phụ trách.
            </p>
          ) : null}
          {!accounts.isPending && !accounts.isError && rows.length === 0 ? (
            <div className="px-6 py-14 text-center" role="status">
              <UsersRound
                aria-hidden="true"
                className="mx-auto size-9 text-neutral-300"
              />
              <h3 className="mt-3 font-bold text-neutral-950">
                Không có tài khoản phù hợp
              </h3>
              <p className="mt-1 text-sm text-neutral-500">
                Thử đổi bộ lọc hoặc tạo tài khoản mới.
              </p>
            </div>
          ) : null}
          {rows.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-[44rem] w-full text-left text-sm">
                <thead className="bg-neutral-50 text-[11px] uppercase tracking-[0.14em] text-neutral-500">
                  <tr>
                    <th className="px-5 py-3 sm:px-6">Tài khoản</th>
                    <th className="px-5 py-3 sm:px-6">Nhiệm vụ</th>
                    <th className="px-5 py-3 sm:px-6">Trạng thái</th>
                    <th className="px-5 py-3 sm:px-6">Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((account) => {
                    const nextStatus =
                      account.status === "ACTIVE"
                        ? "SUSPENDED"
                        : account.status === "SUSPENDED"
                          ? "ACTIVE"
                          : null;
                    const isProtected = account.role === "SUPER_ADMIN";
                    return (
                      <tr
                        className="border-t border-neutral-100"
                        key={account.id}
                      >
                        <td className="px-5 py-4 sm:px-6">
                          <p className="font-semibold text-neutral-950">
                            {account.email}
                          </p>
                          <p className="mt-1 text-xs text-neutral-400">
                            {account.lastLoginAt
                              ? `Đăng nhập ${new Date(account.lastLoginAt).toLocaleDateString("vi-VN")}`
                              : "Chưa đăng nhập"}
                          </p>
                        </td>
                        <td className="px-5 py-4 sm:px-6">
                          <label
                            className="sr-only"
                            htmlFor={`role-${account.id}`}
                          >
                            Nhiệm vụ của {account.email}
                          </label>
                          <SelectControl
                            className="rounded-lg border border-neutral-300 bg-white px-2 py-2 text-xs font-semibold outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 disabled:bg-neutral-100"
                            disabled
                            id={`role-${account.id}`}
                            value={account.role}
                          >
                            {isProtected ? (
                              <option value="SUPER_ADMIN">
                                Quản trị hệ thống
                              </option>
                            ) : null}
                            {STAFF_ACCOUNT_ROLES.map((item) => (
                              <option key={item.value} value={item.value}>
                                {item.label}
                              </option>
                            ))}
                          </SelectControl>
                        </td>
                        <td className="px-5 py-4 sm:px-6">
                          <span className="inline-flex rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs font-bold text-neutral-700">
                            {staffStatusLabel(account.status)}
                          </span>
                        </td>
                        <td className="px-5 py-4 sm:px-6">
                          <div className="flex flex-wrap gap-2">
                            {nextStatus ? (
                              <button
                                aria-label={`${nextStatus === "ACTIVE" ? "Mở khóa" : "Khóa"} ${account.email}`}
                                className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-neutral-300 px-3 text-xs font-bold text-neutral-700 transition hover:border-neutral-500 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
                                disabled={update.isPending || isProtected}
                                onClick={() =>
                                  setPendingUpdate({
                                    id: account.id,
                                    email: account.email,
                                    status: nextStatus,
                                  })
                                }
                                type="button"
                              >
                                <LockKeyhole
                                  aria-hidden="true"
                                  className="size-3.5"
                                />
                                {nextStatus === "ACTIVE" ? "Mở khóa" : "Khóa"}
                              </button>
                            ) : null}
                            {account.status !== "DISABLED" ? (
                              <button
                                aria-label={`Vô hiệu hóa ${account.email}`}
                                className="inline-flex min-h-9 items-center rounded-lg border border-red-200 px-3 text-xs font-bold text-red-700 transition hover:bg-red-50 disabled:opacity-50"
                                disabled={update.isPending || isProtected}
                                onClick={() =>
                                  setPendingUpdate({
                                    id: account.id,
                                    email: account.email,
                                    status: "DISABLED",
                                  })
                                }
                                type="button"
                              >
                                Vô hiệu hóa
                              </button>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
        <ConfirmationDialog
          confirmLabel="Gửi lời mời"
          description={`Lời mời sẽ được gửi tới ${email || "email đã nhập"} cho nhiệm vụ ${selectedRole?.label ?? "đã chọn"}. Người nhận phải xác minh đúng email trước khi làm việc.`}
          isPending={create.isPending}
          onCancel={() => setConfirmInvite(false)}
          onConfirm={() => create.mutate()}
          open={confirmInvite}
          title="Xác nhận mời nhân sự"
        />
        <ConfirmationDialog
          confirmLabel={
            pendingUpdate?.status === "SUSPENDED"
              ? "Khóa tài khoản"
              : pendingUpdate?.status === "DISABLED"
                ? "Vô hiệu hóa"
                : "Xác nhận thay đổi"
          }
          description={
            pendingUpdate?.status === "SUSPENDED"
              ? `Tài khoản ${pendingUpdate.email} sẽ bị khóa và mọi phiên đang mở sẽ kết thúc ngay.`
              : pendingUpdate?.status === "DISABLED"
                ? `Tài khoản ${pendingUpdate.email} sẽ bị vô hiệu hóa, mọi phiên truy cập bị thu hồi và lịch sử công việc vẫn được bảo toàn.`
                : `Tài khoản ${pendingUpdate?.email ?? "này"} sẽ được mở lại. Người dùng vẫn phải hoàn tất các bước bảo vệ tài khoản khi đăng nhập.`
          }
          isPending={update.isPending}
          onCancel={() => setPendingUpdate(null)}
          onConfirm={() => {
            if (pendingUpdate?.status) {
              update.mutate({
                id: pendingUpdate.id,
                email: pendingUpdate.email,
                status: pendingUpdate.status,
              });
            }
          }}
          open={pendingUpdate !== null && !pendingUpdate.role}
          title="Xác nhận trạng thái tài khoản"
        />
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "neutral" | "green" | "red";
}) {
  const toneClass =
    tone === "green"
      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
      : tone === "red"
        ? "border-red-200 bg-red-50 text-red-800"
        : "border-neutral-200 bg-white text-neutral-950";
  return (
    <article className={`rounded-2xl border p-5 shadow-sm ${toneClass}`}>
      <p className="text-sm font-semibold opacity-75">{label}</p>
      <p className="mt-2 text-3xl font-bold">{value}</p>
    </article>
  );
}
function TableSkeleton() {
  return (
    <div
      aria-busy="true"
      aria-label="Đang tải danh sách tài khoản"
      className="space-y-3 p-6"
    >
      {Array.from({ length: 4 }).map((_, index) => (
        <div
          className="h-14 animate-pulse rounded-xl bg-neutral-100"
          key={index}
        />
      ))}
    </div>
  );
}

function staffStatusLabel(status: StaffAccountStatus) {
  const labels: Record<StaffAccountStatus, string> = {
    ACTIVE: "Đang hoạt động",
    SUSPENDED: "Tạm khóa",
    DISABLED: "Đã vô hiệu hóa",
  };
  return labels[status];
}
