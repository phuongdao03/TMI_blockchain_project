"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  MailPlus,
  KeyRound,
  LockKeyhole,
  Search,
  ShieldCheck,
  UserPlus,
  UsersRound,
} from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";

import {
  ApiError,
  staffAccountsApi,
  staffInvitationsApi,
} from "@/lib/api/client";
import type { StaffAccountRole, StaffAccountStatus } from "@/lib/api/types";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { STAFF_ACCOUNT_ROLES } from "./staff-account-roles";

const inputClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-100";

export function StaffAccountWorkspace() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<StaffAccountRole>("REVIEWER");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<StaffAccountStatus | "ALL">("ALL");
  const [roleFilter, setRoleFilter] = useState<StaffAccountRole | "ALL">("ALL");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [recoveryTarget, setRecoveryTarget] = useState<{
    id: string;
    email: string;
  } | null>(null);
  const [recoveryReason, setRecoveryReason] = useState("");
  const [roleChangeReason, setRoleChangeReason] = useState("");
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
  const pendingActions = useQuery({
    queryKey: ["admin", "staff-privileged-actions"],
    queryFn: () => staffAccountsApi.listPendingActions(1, 50),
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
    },
    onError: (cause) =>
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Không thể gửi lời mời lúc này.",
      ),
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
  const requestRoleChange = useMutation({
    mutationFn: () => {
      if (!pendingUpdate?.role) throw new Error("No role change selected");
      return staffAccountsApi.requestRoleChange(
        pendingUpdate.id,
        pendingUpdate.role,
        roleChangeReason.trim(),
      );
    },
    onSuccess: () => {
      setPendingUpdate(null);
      setRoleChangeReason("");
      setFeedback(
        "Đã gửi yêu cầu thay đổi nhiệm vụ. Một quản trị viên khác cần phê duyệt trước khi quyền mới có hiệu lực.",
      );
      setError(null);
      void queryClient.invalidateQueries({
        queryKey: ["admin", "staff-privileged-actions"],
      });
    },
    onError: (cause) =>
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Không thể gửi yêu cầu thay đổi nhiệm vụ.",
      ),
  });
  const recovery = useMutation({
    mutationFn: () => {
      if (!recoveryTarget) throw new Error("No recovery target selected");
      return staffAccountsApi.initiateMfaRecovery(
        recoveryTarget.id,
        recoveryReason.trim(),
      );
    },
    onSuccess: () => {
      setFeedback(
        "Đã gửi yêu cầu khôi phục. Tài khoản chỉ bị tạm khóa sau khi một quản trị viên khác phê duyệt.",
      );
      setError(null);
      setRecoveryTarget(null);
      setRecoveryReason("");
      void queryClient.invalidateQueries({
        queryKey: ["admin", "staff-privileged-actions"],
      });
    },
    onError: (cause) =>
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Không thể bắt đầu khôi phục tài khoản.",
      ),
  });
  const approveAction = useMutation({
    mutationFn: (actionId: string) => staffAccountsApi.approveAction(actionId),
    onSuccess: () => {
      setFeedback(
        "Đã phê duyệt yêu cầu và kết thúc các phiên truy cập liên quan.",
      );
      setError(null);
      void queryClient.invalidateQueries({
        queryKey: ["admin", "staff-privileged-actions"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["admin", "staff-accounts"],
      });
    },
    onError: (cause) =>
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Không thể phê duyệt yêu cầu này.",
      ),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    setError(null);
    setConfirmInvite(true);
  }

  const rows = accounts.data?.data ?? [];
  const activeCount = rows.filter(
    (account) => account.status === "ACTIVE",
  ).length;
  const suspendedCount = rows.filter(
    (account) => account.status === "SUSPENDED",
  ).length;
  const selectedRole = STAFF_ACCOUNT_ROLES.find((item) => item.value === role);

  return (
    <div className="mx-auto max-w-7xl space-y-7 pb-8">
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
          <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">
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
      <section className="border-y border-neutral-200 bg-white px-5 py-5 sm:px-6">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-amber-700">
              Cần xác nhận độc lập
            </p>
            <h2 className="mt-1 text-lg font-bold text-neutral-950">
              Yêu cầu đang chờ phê duyệt
            </h2>
            <p className="mt-1 text-sm text-neutral-600">
              Người tạo yêu cầu không thể tự phê duyệt thay đổi quyền hoặc khôi
              phục bảo vệ.
            </p>
          </div>
          <span className="text-sm font-semibold text-neutral-500">
            {pendingActions.data?.meta.total ?? 0} yêu cầu
          </span>
        </div>
        {pendingActions.isPending ? <TableSkeleton /> : null}
        {!pendingActions.isPending &&
        (pendingActions.data?.data.length ?? 0) === 0 ? (
          <p className="mt-4 border-l-2 border-neutral-200 pl-4 text-sm text-neutral-500">
            Không có yêu cầu nào cần xử lý.
          </p>
        ) : null}
        <div className="mt-4 divide-y divide-neutral-200">
          {(pendingActions.data?.data ?? []).map((action) => {
            const target = rows.find(
              (account) => account.id === action.targetUserId,
            );
            return (
              <article
                className="grid gap-4 py-4 md:grid-cols-[1fr_auto] md:items-center"
                key={action.id}
              >
                <div>
                  <p className="font-semibold text-neutral-950">
                    {action.action === "ROLE_CHANGE"
                      ? `Thay đổi nhiệm vụ${action.requestedRole ? ` · ${action.requestedRole}` : ""}`
                      : "Khôi phục bảo vệ tài khoản"}
                  </p>
                  <p className="mt-1 text-sm text-neutral-600">
                    {target?.email ?? "Tài khoản nội bộ"} · {action.reason}
                  </p>
                  <p className="mt-1 text-xs text-neutral-400">
                    Hết hạn {new Date(action.expiresAt).toLocaleString("vi-VN")}
                  </p>
                </div>
                <button
                  className="min-h-10 rounded-lg bg-neutral-950 px-4 text-sm font-bold text-white transition hover:bg-neutral-800 disabled:opacity-50"
                  disabled={approveAction.isPending}
                  onClick={() => approveAction.mutate(action.id)}
                  type="button"
                >
                  Phê duyệt yêu cầu
                </button>
              </article>
            );
          })}
        </div>
      </section>
      <div className="grid gap-6 xl:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.6fr)]">
        <section className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div className="flex items-start gap-3">
            <span className="rounded-xl bg-neutral-950 p-3 text-white">
              <UserPlus aria-hidden="true" className="size-5" />
            </span>
            <div>
              <h2 className="text-lg font-bold text-neutral-950">
                Tạo lời mời
              </h2>
              <p className="mt-1 text-sm leading-6 text-neutral-600">
                Nhân sự tự xác minh danh tính và đặt thông tin đăng nhập qua
                liên kết bảo mật được gửi tới email công việc.
              </p>
            </div>
          </div>
          <form className="mt-6 space-y-4" onSubmit={submit}>
            <div>
              <label className="text-sm font-semibold" htmlFor="staff-email">
                Email công việc
              </label>
              <input
                className={inputClass}
                id="staff-email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="ten@tmigroup.vn"
                required
                type="email"
                value={email}
              />
            </div>
            <div>
              <label className="text-sm font-semibold" htmlFor="staff-role">
                Nhiệm vụ
              </label>
              <select
                className={inputClass}
                id="staff-role"
                onChange={(event) =>
                  setRole(event.target.value as StaffAccountRole)
                }
                value={role}
              >
                {STAFF_ACCOUNT_ROLES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
              <p className="mt-2 rounded-lg bg-neutral-50 px-3 py-2 text-xs leading-5 text-neutral-600">
                {selectedRole?.description}
              </p>
            </div>
            <button
              className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-neutral-950 px-4 text-sm font-bold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={create.isPending}
              type="submit"
            >
              <MailPlus aria-hidden="true" className="size-4" />
              {create.isPending ? "Đang gửi…" : "Gửi lời mời"}
            </button>
          </form>
          <div className="mt-5 border-t border-neutral-100 pt-4 text-xs leading-5 text-neutral-500">
            Lời mời chỉ dùng một lần và hết hạn sau 24 giờ. Quản trị viên không
            tạo hoặc biết mật khẩu của nhân sự.
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
                <select
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
                  <option value="PENDING_MFA">Chờ hoàn tất bảo vệ</option>
                  <option value="ACTIVE">Đang hoạt động</option>
                  <option value="SUSPENDED">Đã khóa</option>
                  <option value="DISABLED">Đã vô hiệu hóa</option>
                </select>
              </label>
              <label>
                <span className="sr-only">Lọc nhiệm vụ</span>
                <select
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
                </select>
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
                          <select
                            className="rounded-lg border border-neutral-300 bg-white px-2 py-2 text-xs font-semibold outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 disabled:bg-neutral-100"
                            disabled={update.isPending || isProtected}
                            id={`role-${account.id}`}
                            onChange={(event) => {
                              setRoleChangeReason("");
                              setPendingUpdate({
                                id: account.id,
                                email: account.email,
                                role: event.target.value as StaffAccountRole,
                              });
                            }}
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
                          </select>
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
                            {account.status !== "DISABLED" &&
                            account.status !== "PENDING_MFA" ? (
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
                            <button
                              aria-label={`Khôi phục ứng dụng xác thực cho ${account.email}`}
                              className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-amber-300 px-3 text-xs font-bold text-amber-800 transition hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-50"
                              disabled={
                                recovery.isPending ||
                                isProtected ||
                                account.status !== "ACTIVE"
                              }
                              onClick={() => {
                                setRecoveryTarget({
                                  id: account.id,
                                  email: account.email,
                                });
                                setRecoveryReason("");
                              }}
                              type="button"
                            >
                              <KeyRound
                                aria-hidden="true"
                                className="size-3.5"
                              />
                              Khôi phục bảo vệ
                            </button>
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
        {pendingUpdate?.role ? (
          <div
            aria-labelledby="staff-role-change-title"
            aria-modal="true"
            className="fixed inset-0 z-50 grid place-items-center bg-neutral-950/70 p-4 backdrop-blur-sm"
            role="dialog"
          >
            <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
              <h2
                className="text-xl font-bold text-neutral-950"
                id="staff-role-change-title"
              >
                Yêu cầu thay đổi nhiệm vụ
              </h2>
              <p className="mt-2 text-sm leading-6 text-neutral-600">
                Thay đổi của {pendingUpdate.email} chỉ có hiệu lực sau khi một
                quản trị viên khác kiểm tra và phê duyệt.
              </p>
              <label
                className="mt-5 block text-sm font-semibold text-neutral-900"
                htmlFor="staff-role-change-reason"
              >
                Căn cứ thay đổi
              </label>
              <textarea
                className={`${inputClass} min-h-28 resize-y py-3`}
                id="staff-role-change-reason"
                maxLength={500}
                onChange={(event) => setRoleChangeReason(event.target.value)}
                placeholder="Ví dụ: Điều chuyển nhiệm vụ theo quyết định nhân sự đã được xác nhận."
                value={roleChangeReason}
              />
              <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button
                  className="min-h-11 rounded-lg px-4 text-sm font-bold text-neutral-600 hover:bg-neutral-100"
                  disabled={requestRoleChange.isPending}
                  onClick={() => setPendingUpdate(null)}
                  type="button"
                >
                  Hủy
                </button>
                <button
                  className="min-h-11 rounded-lg bg-neutral-950 px-4 text-sm font-bold text-white disabled:opacity-50"
                  disabled={
                    requestRoleChange.isPending ||
                    roleChangeReason.trim().length < 10
                  }
                  onClick={() => requestRoleChange.mutate()}
                  type="button"
                >
                  {requestRoleChange.isPending
                    ? "Đang gửi…"
                    : "Gửi yêu cầu phê duyệt"}
                </button>
              </div>
            </div>
          </div>
        ) : null}
        {recoveryTarget ? (
          <div
            aria-labelledby="staff-recovery-title"
            aria-modal="true"
            className="fixed inset-0 z-50 grid place-items-center bg-neutral-950/70 p-4 backdrop-blur-sm"
            role="dialog"
          >
            <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
              <h2
                className="text-xl font-bold text-neutral-950"
                id="staff-recovery-title"
              >
                Khôi phục bảo vệ tài khoản
              </h2>
              <p className="mt-2 text-sm leading-6 text-neutral-600">
                Yêu cầu cho {recoveryTarget.email} cần một quản trị viên khác
                phê duyệt. Khi được duyệt, mọi phiên đang mở mới bị kết thúc.
              </p>
              <label
                className="mt-5 block text-sm font-semibold text-neutral-900"
                htmlFor="staff-recovery-reason"
              >
                Lý do khôi phục
              </label>
              <textarea
                className={`${inputClass} min-h-28 resize-y py-3`}
                id="staff-recovery-reason"
                maxLength={500}
                onChange={(event) => setRecoveryReason(event.target.value)}
                placeholder="Ví dụ: Nhân sự đã xác minh danh tính và mất thiết bị cũ."
                value={recoveryReason}
              />
              <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button
                  className="min-h-11 rounded-lg px-4 text-sm font-bold text-neutral-600 hover:bg-neutral-100"
                  disabled={recovery.isPending}
                  onClick={() => setRecoveryTarget(null)}
                  type="button"
                >
                  Hủy
                </button>
                <button
                  className="min-h-11 rounded-lg bg-amber-700 px-4 text-sm font-bold text-white disabled:opacity-50"
                  disabled={
                    recovery.isPending || recoveryReason.trim().length < 10
                  }
                  onClick={() => recovery.mutate()}
                  type="button"
                >
                  {recovery.isPending ? "Đang xử lý…" : "Gửi yêu cầu khôi phục"}
                </button>
              </div>
            </div>
          </div>
        ) : null}
        <ConfirmationDialog
          confirmLabel="Gửi lời mời"
          description={`Lời mời sẽ được gửi tới ${email || "email đã nhập"} cho nhiệm vụ ${selectedRole?.label ?? "đã chọn"}. Người nhận phải xác minh đúng email và thiết lập bảo vệ tài khoản trước khi làm việc.`}
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
            if (
              pendingUpdate?.status &&
              pendingUpdate.status !== "PENDING_MFA"
            ) {
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
    PENDING_MFA: "Chờ hoàn tất bảo vệ",
    ACTIVE: "Đang hoạt động",
    SUSPENDED: "Tạm khóa",
    DISABLED: "Đã vô hiệu hóa",
  };
  return labels[status];
}
