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

import { adminUsersApi, ApiError } from "@/lib/api/client";
import type { AdminUser, AdminUserStatus } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";

const fieldClass =
  "min-h-11 rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-100";

const statusLabel: Record<AdminUserStatus, string> = {
  PENDING: "Chờ kích hoạt",
  ACTIVE: "Đang hoạt động",
  SUSPENDED: "Đã đình chỉ",
  DELETED: "Đã xóa mềm",
};

function formatDate(value: string | null) {
  if (!value) return "Chưa có";
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(
    new Date(value),
  );
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
  const [reason, setReason] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const canSuspend = authUser?.permissions?.includes("users.suspend") ?? false;
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
  const rows = users.data?.data ?? [];
  const total = users.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / 20));

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setSearch(draftSearch.trim());
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
              placeholder="Tên, email hoặc UUID"
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
            className="hidden overflow-x-auto rounded-2xl border border-neutral-200 bg-white md:block"
            data-testid="admin-users-table"
          >
            <table className="w-full min-w-[850px] text-left text-sm">
              <thead className="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
                <tr>
                  <th className="px-5 py-4">Người dùng</th>
                  <th className="px-5 py-4">Xác minh</th>
                  <th className="px-5 py-4">Vai trò</th>
                  <th className="px-5 py-4">Trạng thái</th>
                  <th className="px-5 py-4">Đăng nhập cuối</th>
                  {canSuspend ? (
                    <th className="px-5 py-4 text-right">Thao tác</th>
                  ) : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {rows.map((user) => (
                  <tr key={user.id}>
                    <td className="px-5 py-4">
                      <p className="font-bold text-neutral-950">
                        {user.fullName || "Chưa cập nhật tên"}
                      </p>
                      <p className="mt-1 text-neutral-500">{user.email}</p>
                    </td>
                    <td className="px-5 py-4">
                      {user.isEmailVerified ? "Đã xác minh" : "Chưa xác minh"}
                    </td>
                    <td className="px-5 py-4">
                      {user.roles.join(", ") || "—"}
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge status={user.status} />
                    </td>
                    <td className="px-5 py-4">
                      {formatDate(user.lastLoginAt)}
                    </td>
                    {canSuspend ? (
                      <td className="px-5 py-4 text-right">
                        <UserAction onSelect={setTarget} user={user} />
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="space-y-3 md:hidden" data-testid="admin-users-mobile">
            {rows.map((user) => (
              <article
                className="rounded-2xl border border-neutral-200 bg-white p-4"
                key={user.id}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="truncate font-bold text-neutral-950">
                      {user.fullName || "Chưa cập nhật tên"}
                    </h2>
                    <p className="mt-1 truncate text-sm text-neutral-500">
                      {user.email}
                    </p>
                  </div>
                  <StatusBadge status={user.status} />
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-neutral-100 pt-4 text-sm">
                  <div>
                    <dt className="text-neutral-500">Vai trò</dt>
                    <dd className="mt-1 font-semibold text-neutral-900">
                      {user.roles.join(", ") || "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-neutral-500">Đăng nhập cuối</dt>
                    <dd className="mt-1 font-semibold text-neutral-900">
                      {formatDate(user.lastLoginAt)}
                    </dd>
                  </div>
                </dl>
                {canSuspend ? (
                  <div className="mt-4">
                    <UserAction onSelect={setTarget} user={user} />
                  </div>
                ) : null}
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
              Thao tác được kiểm tra quyền ở máy chủ và ghi vào audit log.
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
