"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  Search,
  ShieldAlert,
  Users,
} from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  adminUsersApi,
  auditApi,
  ApiError,
  staffInvitationsApi,
} from "@/lib/api/client";
import type {
  AdminUser,
  AdminUserStatus,
  StaffInvitation,
} from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";

const fieldClass =
  "min-h-11 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm text-[var(--theme-text)] outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-100";

const statusLabel: Record<AdminUserStatus, string> = {
  PENDING: "Chờ kích hoạt",
  ACTIVE: "Đang hoạt động",
  SUSPENDED: "Đã đình chỉ",
  DELETED: "Đã xóa mềm",
};

const roleLabel: Record<string, string> = {
  SUPER_ADMIN: "Quản trị hệ thống",
  MODERATOR: "Người kiểm duyệt",
  USER: "Người nộp hồ sơ",
  VIEWER: "Người tra cứu",
};

function formatRoles(roles: string[]) {
  return roles.map((role) => roleLabel[role] ?? role).join(", ") || "—";
}

function formatDate(value: string | null) {
  if (!value) return "Chưa có";
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(
    new Date(value),
  );
}

function auditReason(entry: { after: Record<string, unknown> | null }) {
  const reason = entry.after?.reason;
  return typeof reason === "string"
    ? reason
    : "Thay đổi được ghi nhận trong nhật ký.";
}

function testInvitationErrorMessage(error: unknown) {
  if (
    error instanceof ApiError &&
    error.code === "TEST_APPLICANT_MUST_BE_NEW"
  ) {
    return "Email này đã có tài khoản. Không thể chuyển tài khoản hiện tại sang TEST; hãy dùng email mới để giữ nguyên dữ liệu thật.";
  }
  return error instanceof ApiError
    ? error.message
    : "Chưa thể gửi lời mời TEST. Vui lòng thử lại.";
}

function StatusBadge({ status }: { status: AdminUserStatus }) {
  const tone =
    status === "ACTIVE"
      ? "bg-emerald-50 text-emerald-800"
      : status === "SUSPENDED"
        ? "bg-amber-50 text-amber-800"
        : "bg-neutral-100 text-neutral-700";
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${tone}`}
    >
      {statusLabel[status]}
    </span>
  );
}

function UserAction({
  user,
  onSelect,
}: {
  user: AdminUser;
  onSelect: (user: AdminUser) => void;
}) {
  if (!(["ACTIVE", "SUSPENDED"] as AdminUserStatus[]).includes(user.status))
    return null;
  return (
    <button
      className="min-h-11 rounded-xl border border-neutral-300 px-3 text-sm font-bold text-neutral-800 transition hover:border-neutral-500 hover:bg-neutral-50"
      onClick={() => onSelect(user)}
      type="button"
    >
      {user.status === "ACTIVE" ? "Tạm đình chỉ" : "Khôi phục"}
    </button>
  );
}

export function AdminUserWorkspace() {
  const authUser = useAuthUser();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [draftSearch, setDraftSearch] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<AdminUserStatus | "">("");
  const [sortBy, setSortBy] = useState<"createdAt" | "email" | "lastLoginAt">(
    "createdAt",
  );
  const [target, setTarget] = useState<AdminUser | null>(null);
  const [detailUser, setDetailUser] = useState<AdminUser | null>(null);
  const [pendingExemptionChange, setPendingExemptionChange] = useState<
    boolean | null
  >(null);
  const [testApplicantEmail, setTestApplicantEmail] = useState("");
  const [createdTestInvitation, setCreatedTestInvitation] =
    useState<StaffInvitation | null>(null);
  const [reason, setReason] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const canSuspend = authUser?.permissions?.includes("users.suspend") ?? false;
  const canManageTestAccounts =
    authUser?.roles.includes("SUPER_ADMIN") === true ||
    (authUser?.permissions?.includes("admin.staff.manage") ?? false);
  const canReadAudit =
    authUser?.roles.includes("SUPER_ADMIN") === true ||
    (authUser?.permissions?.includes("audit.read") ?? false);
  const users = useQuery({
    queryKey: ["admin", "users", page, search, status, sortBy],
    queryFn: () =>
      adminUsersApi.list({
        page,
        pageSize: 20,
        search: search || undefined,
        status: status || undefined,
        sortBy,
        sortOrder: sortBy === "email" ? "asc" : "desc",
      }),
  });
  const selectedUser = useQuery({
    queryKey: ["admin", "user", detailUser?.id],
    queryFn: () => adminUsersApi.detail(detailUser!.id),
    enabled: detailUser !== null,
  });
  const userHistory = useQuery({
    queryKey: ["admin", "audit", "user", detailUser?.id],
    queryFn: () =>
      auditApi.list({
        page: 1,
        pageSize: 20,
        resourceType: "user",
        resourceId: detailUser!.id,
      }),
    enabled: detailUser !== null && canReadAudit,
  });
  const createTestApplicant = useMutation({
    mutationFn: () =>
      staffInvitationsApi.createTestApplicant(testApplicantEmail.trim()),
    onSuccess: (invitation) => {
      setCreatedTestInvitation(invitation);
      setTestApplicantEmail("");
      setFeedback(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
  const updateStatus = useMutation({
    mutationFn: () => {
      if (!target) throw new Error("Missing user status target");
      return adminUsersApi.changeStatus(target.id, {
        status: target.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE",
        expectedStatus: target.status,
        reason: reason.trim(),
      });
    },
    onSuccess: () => {
      setFeedback(
        target?.status === "ACTIVE"
          ? "Đã đình chỉ tài khoản và thu hồi các phiên đăng nhập."
          : "Đã khôi phục tài khoản.",
      );
      setTarget(null);
      setReason("");
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
  const updateSubmissionFeeTestExemption = useMutation({
    mutationFn: (enabled: boolean) => {
      if (!detailUser) throw new Error("Missing user exemption target");
      return adminUsersApi.setSubmissionFeeTestExemption(
        detailUser.id,
        enabled,
      );
    },
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(["admin", "user", updatedUser.id], updatedUser);
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      void queryClient.invalidateQueries({
        queryKey: ["admin", "audit", "user", updatedUser.id],
      });
      setPendingExemptionChange(null);
      setFeedback(
        updatedUser.submissionFeeTestExemption
          ? "Đã bật quyền miễn phí nộp hồ sơ kiểm thử."
          : "Đã tắt quyền miễn phí nộp hồ sơ kiểm thử.",
      );
    },
  });
  const rows = users.data?.data ?? [];
  const total = users.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / 20));
  const displayedUser = selectedUser.data ?? detailUser;
  const historyEntries = userHistory.data?.data ?? [];

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setSearch(draftSearch.trim());
  }

  function submitTestInvitation(event: FormEvent) {
    event.preventDefault();
    if (!testApplicantEmail.trim()) return;
    createTestApplicant.mutate();
  }

  return (
    <section
      aria-labelledby="admin-users-title"
      className="mx-auto max-w-7xl space-y-6 pb-10"
    >
      <header className="border-b border-neutral-200 pb-6">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
          <Users aria-hidden="true" className="size-4" />
          Quản trị tài khoản
        </p>
        <h1
          className="mt-2 text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl"
          id="admin-users-title"
        >
          Người dùng
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
          Tra cứu tài khoản, kiểm tra trạng thái xác minh và xử lý truy cập bằng
          dữ liệu trực tiếp từ hệ thống.
        </p>
      </header>

      {canManageTestAccounts ? (
        <details className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4">
          <summary className="cursor-pointer text-sm font-semibold text-[var(--theme-muted)]">
            Mời tài khoản TEST mới (tùy chọn)
          </summary>
          <div className="mt-3 space-y-3">
            <p className="text-sm leading-6 text-[var(--theme-muted)]">
              Dùng cho tài khoản chưa đăng ký. Để miễn phí nộp hồ sơ cho tài
              khoản hiện có, hãy mở chi tiết tài khoản trong danh sách.
            </p>
            <form
              className="flex flex-col gap-2 sm:flex-row sm:items-end"
              onSubmit={submitTestInvitation}
            >
              <label className="min-w-0 flex-1 text-sm font-semibold text-[var(--theme-text)]">
                Email mới
                <input
                  aria-label="Email tài khoản TEST mới"
                  className={`${fieldClass} mt-1.5 w-full`}
                  onChange={(event) =>
                    setTestApplicantEmail(event.target.value)
                  }
                  placeholder="tester@example.com"
                  required
                  type="email"
                  value={testApplicantEmail}
                />
              </label>
              <button
                className="min-h-11 rounded-xl bg-[var(--theme-text)] px-4 text-sm font-bold text-[var(--theme-surface)] disabled:opacity-50 sm:shrink-0"
                disabled={createTestApplicant.isPending}
                type="submit"
              >
                {createTestApplicant.isPending
                  ? "Đang gửi…"
                  : "Gửi lời mời TEST"}
              </button>
            </form>
            {createTestApplicant.isError ? (
              <p className="text-sm font-medium text-red-700" role="alert">
                {testInvitationErrorMessage(createTestApplicant.error)}
              </p>
            ) : null}
            {createdTestInvitation ? (
              <p className="text-sm text-emerald-800" role="status">
                Đã gửi lời mời TEST đến {createdTestInvitation.email}. Trạng
                thái: {createdTestInvitation.status}. Hệ thống đã ghi nhật ký.
              </p>
            ) : null}
          </div>
        </details>
      ) : null}

      <form
        className="grid gap-3 rounded-2xl border border-neutral-200 bg-white p-4 md:grid-cols-[1fr_12rem_12rem_auto]"
        onSubmit={submitSearch}
      >
        <label className="text-sm font-bold text-neutral-800">
          Tìm kiếm
          <span className="relative mt-2 block">
            <Search
              aria-hidden="true"
              className="absolute left-3 top-3.5 size-4 text-neutral-400"
            />
            <input
              aria-label="Tìm theo tên, email hoặc mã người dùng"
              className={`${fieldClass} w-full pl-10`}
              onChange={(event) => setDraftSearch(event.target.value)}
              placeholder="Tìm theo tên hoặc email"
              type="search"
              value={draftSearch}
            />
          </span>
        </label>
        <label className="text-sm font-bold text-neutral-800">
          Trạng thái
          <select
            className={`${fieldClass} mt-2 w-full`}
            onChange={(event) => {
              setPage(1);
              setStatus(event.target.value as AdminUserStatus | "");
            }}
            value={status}
          >
            <option value="">Tất cả</option>
            {Object.entries(statusLabel).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-bold text-neutral-800">
          Sắp xếp
          <select
            className={`${fieldClass} mt-2 w-full`}
            onChange={(event) => {
              setPage(1);
              setSortBy(event.target.value as typeof sortBy);
            }}
            value={sortBy}
          >
            <option value="createdAt">Mới đăng ký</option>
            <option value="lastLoginAt">Đăng nhập gần nhất</option>
            <option value="email">Email A–Z</option>
          </select>
        </label>
        <button
          className="min-h-11 self-end rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white transition hover:bg-neutral-800"
          type="submit"
        >
          Áp dụng
        </button>
      </form>

      {feedback ? (
        <p
          className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800"
          role="status"
        >
          {feedback}
        </p>
      ) : null}
      {users.isLoading ? (
        <div
          aria-label="Đang tải người dùng"
          className="h-72 animate-pulse rounded-2xl bg-neutral-100"
          role="status"
        />
      ) : null}
      {users.isError ? (
        <div
          className="rounded-2xl border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <p className="font-bold text-red-900">
            {users.error instanceof ApiError && users.error.status === 403
              ? "Bạn không có quyền xem người dùng"
              : "Không thể tải danh sách người dùng"}
          </p>
          <p className="mt-1 text-sm text-red-700">
            {users.error instanceof ApiError
              ? users.error.message
              : "Vui lòng thử lại."}
          </p>
          <button
            className="mt-4 min-h-11 rounded-xl border border-red-300 px-4 text-sm font-bold text-red-900"
            onClick={() => void users.refetch()}
            type="button"
          >
            Thử lại
          </button>
        </div>
      ) : null}
      {!users.isLoading && !users.isError && rows.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-neutral-300 p-10 text-center">
          <p className="font-bold text-neutral-900">
            Không tìm thấy người dùng
          </p>
          <p className="mt-1 text-sm text-neutral-600">
            Thử điều chỉnh từ khóa hoặc bộ lọc.
          </p>
        </div>
      ) : null}

      {rows.length ? (
        <>
          <div
            className="hidden overflow-x-auto rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] md:block"
            data-testid="admin-users-table"
          >
            <table className="w-full min-w-[880px] text-left text-sm text-[var(--theme-text)]">
              <thead className="bg-[var(--theme-elevated)] text-xs uppercase tracking-wide text-[var(--theme-muted)]">
                <tr>
                  <th className="px-5 py-4">Người dùng</th>
                  <th className="px-5 py-4">Xác minh</th>
                  <th className="px-5 py-4">Vai trò</th>
                  <th className="px-5 py-4">Trạng thái</th>
                  <th className="px-5 py-4">Đăng nhập cuối</th>
                  <th className="px-5 py-4 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {rows.map((user) => (
                  <tr key={user.id}>
                    <td className="px-5 py-4">
                      <p className="font-bold text-neutral-950">
                        {user.fullName || "Chưa cập nhật tên"}
                      </p>
                      {user.isTestAccount ? (
                        <span className="mt-1 inline-flex rounded-full bg-amber-500/10 px-2 py-0.5 text-xs font-bold text-amber-800">
                          Tài khoản TEST
                        </span>
                      ) : null}
                      {user.submissionFeeTestExemption ? (
                        <span className="mt-1 inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-800">
                          Miễn phí kiểm thử
                        </span>
                      ) : null}
                      <p className="mt-1 text-neutral-600">{user.email}</p>
                    </td>
                    <td className="px-5 py-4">
                      {user.isEmailVerified ? "Đã xác minh" : "Chưa xác minh"}
                    </td>
                    <td className="px-5 py-4">{formatRoles(user.roles)}</td>
                    <td className="px-5 py-4">
                      <StatusBadge status={user.status} />
                    </td>
                    <td className="px-5 py-4">
                      {formatDate(user.lastLoginAt)}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          className="min-h-10 rounded-xl border border-[var(--theme-border)] px-3 text-sm font-semibold text-[var(--theme-text)]"
                          onClick={() => setDetailUser(user)}
                          type="button"
                        >
                          Xem chi tiết
                        </button>
                        {canSuspend ? (
                          <UserAction onSelect={setTarget} user={user} />
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="space-y-3 md:hidden" data-testid="admin-users-mobile">
            {rows.map((user) => (
              <article
                className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4"
                key={user.id}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="truncate font-bold text-neutral-950">
                      {user.fullName || "Chưa cập nhật tên"}
                    </h2>
                    {user.isTestAccount ? (
                      <span className="mt-1 inline-flex rounded-full bg-amber-500/10 px-2 py-0.5 text-xs font-bold text-amber-800">
                        Tài khoản TEST
                      </span>
                    ) : null}
                    {user.submissionFeeTestExemption ? (
                      <span className="mt-1 inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-800">
                        Miễn phí kiểm thử
                      </span>
                    ) : null}
                    <p className="mt-1 truncate text-sm text-neutral-600">
                      {user.email}
                    </p>
                  </div>
                  <StatusBadge status={user.status} />
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-neutral-100 pt-4 text-sm">
                  <div>
                    <dt className="text-neutral-600">Vai trò</dt>
                    <dd className="mt-1 font-semibold text-neutral-900">
                      {formatRoles(user.roles)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-neutral-600">Đăng nhập cuối</dt>
                    <dd className="mt-1 font-semibold text-neutral-900">
                      {formatDate(user.lastLoginAt)}
                    </dd>
                  </div>
                </dl>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    className="min-h-11 rounded-xl border border-[var(--theme-border)] px-3 text-sm font-semibold text-[var(--theme-text)]"
                    onClick={() => setDetailUser(user)}
                    type="button"
                  >
                    Xem chi tiết
                  </button>
                  {canSuspend ? (
                    <UserAction onSelect={setTarget} user={user} />
                  ) : null}
                </div>
              </article>
            ))}
          </div>
          <div className="flex items-center justify-between">
            <p className="text-sm text-neutral-600">
              {total.toLocaleString("vi-VN")} tài khoản
            </p>
            <div className="flex items-center gap-2">
              <button
                aria-label="Trang trước"
                className="grid min-h-11 min-w-11 place-items-center rounded-xl border border-neutral-300 disabled:opacity-40"
                disabled={page === 1}
                onClick={() => setPage((value) => value - 1)}
                type="button"
              >
                <ChevronLeft aria-hidden="true" className="size-4" />
              </button>
              <span className="text-sm font-bold">
                {page}/{pageCount}
              </span>
              <button
                aria-label="Trang sau"
                className="grid min-h-11 min-w-11 place-items-center rounded-xl border border-neutral-300 disabled:opacity-40"
                disabled={page >= pageCount}
                onClick={() => setPage((value) => value + 1)}
                type="button"
              >
                <ChevronRight aria-hidden="true" className="size-4" />
              </button>
            </div>
          </div>
        </>
      ) : null}

      {detailUser ? (
        <div
          aria-labelledby="user-detail-title"
          aria-modal="true"
          className="fixed inset-0 z-50 grid place-items-end bg-neutral-950/70 p-0 sm:place-items-center sm:p-4"
          role="dialog"
        >
          <section className="max-h-[90dvh] w-full space-y-5 overflow-y-auto overscroll-contain rounded-t-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 text-[var(--theme-text)] sm:max-w-xl sm:rounded-2xl sm:p-6">
            <header className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-wide text-primary-700">
                  Hồ sơ tài khoản
                </p>
                <h2
                  className="mt-1 truncate text-xl font-bold"
                  id="user-detail-title"
                >
                  Chi tiết tài khoản
                </h2>
                {displayedUser ? (
                  <p className="mt-1 break-all text-sm text-[var(--theme-muted)]">
                    {displayedUser.fullName || displayedUser.email} ·{" "}
                    {displayedUser.email}
                  </p>
                ) : null}
              </div>
              <button
                aria-label="Đóng chi tiết"
                className="grid size-11 shrink-0 place-items-center rounded-xl border border-[var(--theme-border)] font-bold"
                onClick={() => {
                  setPendingExemptionChange(null);
                  setDetailUser(null);
                }}
                type="button"
              >
                ×
              </button>
            </header>
            {selectedUser.isLoading ? (
              <p aria-busy="true" role="status">
                Đang tải thông tin tài khoản…
              </p>
            ) : selectedUser.isError ? (
              <p className="text-sm text-red-700" role="alert">
                Không thể tải chi tiết tài khoản.
              </p>
            ) : displayedUser ? (
              <>
                <dl className="grid grid-cols-2 gap-4 rounded-xl bg-[var(--theme-elevated)] p-4 text-sm">
                  <div>
                    <dt className="text-[var(--theme-muted)]">
                      Vai trò hiện tại
                    </dt>
                    <dd className="mt-1 font-semibold">
                      {formatRoles(displayedUser.roles)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--theme-muted)]">
                      Trạng thái hoạt động
                    </dt>
                    <dd className="mt-1 font-semibold">
                      {statusLabel[displayedUser.status]}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--theme-muted)]">
                      Trạng thái kiểm thử
                    </dt>
                    <dd className="mt-1 font-semibold">
                      {displayedUser.isTestAccount
                        ? "Tài khoản TEST"
                        : "Tài khoản thật"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--theme-muted)]">Email</dt>
                    <dd className="mt-1 break-all font-semibold">
                      {displayedUser.email}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--theme-muted)]">Ngày tạo</dt>
                    <dd className="mt-1 font-semibold">
                      {formatDate(displayedUser.createdAt)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--theme-muted)]">
                      Đăng nhập gần nhất
                    </dt>
                    <dd className="mt-1 font-semibold">
                      {formatDate(displayedUser.lastLoginAt)}
                    </dd>
                  </div>
                </dl>
                <p className="rounded-xl border border-amber-300/70 bg-amber-500/5 p-3 text-sm leading-6">
                  {displayedUser.isTestAccount
                    ? "Tài khoản này có cờ TEST riêng. Quyền miễn phí nộp bên dưới chỉ áp dụng cho phí nộp hồ sơ."
                    : "Quyền miễn phí nộp bên dưới không đổi phân loại tài khoản, lịch sử hoặc thao tác ví."}
                </p>
                {canManageTestAccounts &&
                displayedUser.roles.length === 1 &&
                displayedUser.roles[0] === "USER" ? (
                  <section
                    aria-labelledby="submission-fee-test-exemption-title"
                    className="space-y-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4"
                  >
                    <div>
                      <h3
                        className="font-bold"
                        id="submission-fee-test-exemption-title"
                      >
                        Miễn phí nộp hồ sơ kiểm thử
                      </h3>
                      <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
                        Chỉ miễn phí nộp hồ sơ mới. Không cấp vai trò, không đổi
                        cờ TEST và không miễn phí dịch vụ khác.
                      </p>
                    </div>
                    <p className="text-sm font-semibold">
                      {displayedUser.submissionFeeTestExemption
                        ? "Đang bật"
                        : "Đang tắt"}
                    </p>
                    {displayedUser.submissionFeeTestExemptionChangedAt ? (
                      <p className="break-all text-xs text-[var(--theme-muted)]">
                        Cập nhật{" "}
                        {formatDate(
                          displayedUser.submissionFeeTestExemptionChangedAt,
                        )}
                        {displayedUser.submissionFeeTestExemptionChangedByUserId
                          ? ` · người thực hiện ${displayedUser.submissionFeeTestExemptionChangedByUserId}`
                          : ""}
                      </p>
                    ) : null}
                    <button
                      className="min-h-11 w-full rounded-xl border border-[var(--theme-border)] px-4 text-sm font-bold sm:w-auto"
                      disabled={
                        updateSubmissionFeeTestExemption.isPending ||
                        (displayedUser.status !== "ACTIVE" &&
                          !displayedUser.submissionFeeTestExemption)
                      }
                      onClick={() =>
                        setPendingExemptionChange(
                          !displayedUser.submissionFeeTestExemption,
                        )
                      }
                      type="button"
                    >
                      {updateSubmissionFeeTestExemption.isPending
                        ? "Đang cập nhật…"
                        : displayedUser.submissionFeeTestExemption
                          ? "Tắt kiểm thử miễn phí"
                          : "Bật kiểm thử miễn phí"}
                    </button>
                    {updateSubmissionFeeTestExemption.error ? (
                      <p className="text-sm text-red-700" role="alert">
                        Không thể cập nhật quyền miễn phí nộp. Hãy tải lại tài
                        khoản và thử lại.
                      </p>
                    ) : null}
                  </section>
                ) : null}
                {pendingExemptionChange !== null ? (
                  <section
                    aria-labelledby="confirm-test-exemption-title"
                    className="space-y-3 rounded-xl border border-primary-300 bg-primary-50 p-4 text-primary-950"
                    role="group"
                    aria-label="Xác nhận thay đổi quyền miễn phí kiểm thử"
                  >
                    <h3 className="font-bold" id="confirm-test-exemption-title">
                      {pendingExemptionChange
                        ? "Bật miễn phí kiểm thử?"
                        : "Tắt miễn phí kiểm thử?"}
                    </h3>
                    <p className="text-sm leading-6">
                      {pendingExemptionChange
                        ? "Tài khoản này sẽ được miễn phí khi nộp hồ sơ để phục vụ kiểm thử. Các giao dịch và hồ sơ đã phát sinh trước đó không bị thay đổi."
                        : "Các lần nộp hồ sơ mới sẽ áp dụng mức phí chung. Hồ sơ và giao dịch đã phát sinh không bị thay đổi."}
                    </p>
                    <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                      <button
                        className="min-h-11 rounded-xl border border-primary-300 px-4 text-sm font-bold"
                        disabled={updateSubmissionFeeTestExemption.isPending}
                        onClick={() => setPendingExemptionChange(null)}
                        type="button"
                      >
                        Hủy
                      </button>
                      <button
                        className="min-h-11 rounded-xl bg-primary-700 px-4 text-sm font-bold text-white disabled:opacity-50"
                        disabled={updateSubmissionFeeTestExemption.isPending}
                        onClick={() =>
                          updateSubmissionFeeTestExemption.mutate(
                            pendingExemptionChange,
                          )
                        }
                        type="button"
                      >
                        {updateSubmissionFeeTestExemption.isPending
                          ? "Đang cập nhật…"
                          : "Xác nhận"}
                      </button>
                    </div>
                  </section>
                ) : null}
                <section aria-labelledby="user-history-title">
                  <h3 className="font-bold" id="user-history-title">
                    Nhật ký thay đổi
                  </h3>
                  {!canReadAudit ? (
                    <p className="mt-2 text-sm text-[var(--theme-muted)]">
                      Tài khoản hiện tại không có quyền xem nhật ký kiểm toán.
                    </p>
                  ) : userHistory.isPending ? (
                    <p className="mt-2 text-sm" aria-busy="true">
                      Đang tải nhật ký…
                    </p>
                  ) : userHistory.isError ? (
                    <p className="mt-2 text-sm text-red-700" role="alert">
                      Không thể tải nhật ký thay đổi.
                    </p>
                  ) : historyEntries.length ? (
                    <ol className="mt-3 divide-y divide-[var(--theme-border)] rounded-xl border border-[var(--theme-border)] px-3">
                      {historyEntries.map((entry) => (
                        <li className="py-3" key={entry.id}>
                          <p className="text-sm font-semibold">
                            {entry.action === "admin.user.status_changed"
                              ? "Cập nhật trạng thái tài khoản"
                              : entry.action ===
                                  "admin.user.submission_fee_test_exemption_changed"
                                ? "Cập nhật quyền miễn phí nộp hồ sơ kiểm thử"
                                : entry.action}
                          </p>
                          <p className="mt-1 text-xs text-[var(--theme-muted)]">
                            {formatDate(entry.createdAt)} · {auditReason(entry)}
                          </p>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="mt-2 text-sm text-[var(--theme-muted)]">
                      Chưa có thay đổi nào được ghi nhận.
                    </p>
                  )}
                </section>
              </>
            ) : null}
            <button
              className="min-h-11 w-full rounded-xl border border-[var(--theme-border)] px-4 text-sm font-bold sm:w-auto"
              onClick={() => setDetailUser(null)}
              type="button"
            >
              Đóng
            </button>
          </section>
        </div>
      ) : null}

      {target ? (
        <div
          aria-labelledby="status-dialog-title"
          aria-modal="true"
          className="fixed inset-0 z-50 grid place-items-end bg-neutral-950/70 p-0 sm:place-items-center sm:p-4"
          role="dialog"
        >
          <div className="w-full rounded-t-2xl bg-white p-5 sm:max-w-md sm:rounded-2xl sm:p-6">
            <ShieldAlert aria-hidden="true" className="size-6 text-amber-700" />
            <h2 className="mt-3 text-xl font-bold" id="status-dialog-title">
              {target.status === "ACTIVE"
                ? "Đình chỉ tài khoản"
                : "Khôi phục tài khoản"}
            </h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              Quyền được kiểm tra trước khi lưu thay đổi. Lịch sử thao tác sẽ
              được lưu lại.
            </p>
            <label className="mt-5 block text-sm font-bold">
              Lý do thay đổi trạng thái
              <textarea
                aria-label="Lý do thay đổi trạng thái"
                className={`${fieldClass} mt-2 min-h-28 w-full py-3`}
                onChange={(event) => setReason(event.target.value)}
                value={reason}
              />
            </label>
            {updateStatus.isError ? (
              <p className="mt-3 text-sm text-red-700" role="alert">
                Không thể cập nhật. Hãy tải lại và thử lại.
              </p>
            ) : null}
            <div className="mt-5 grid grid-cols-2 gap-3">
              <button
                className="min-h-11 rounded-xl border border-neutral-300 font-bold"
                onClick={() => {
                  setTarget(null);
                  setReason("");
                }}
                type="button"
              >
                Hủy
              </button>
              <button
                className="min-h-11 rounded-xl bg-neutral-950 px-3 font-bold text-white disabled:opacity-40"
                disabled={reason.trim().length < 10 || updateStatus.isPending}
                onClick={() => updateStatus.mutate()}
                type="button"
              >
                {target.status === "ACTIVE"
                  ? "Xác nhận đình chỉ"
                  : "Xác nhận khôi phục"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
