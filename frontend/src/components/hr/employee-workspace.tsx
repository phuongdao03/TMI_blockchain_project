"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BriefcaseBusiness,
  Plus,
  Search,
  UserRoundPlus,
  X,
} from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  adminUsersApi,
  ApiError,
  employeeInvitationsApi,
  hrDepartmentApi,
  hrEmployeeApi,
} from "@/lib/api/client";
import type { Employee, EmploymentStatus } from "@/lib/api/types";
import { HrReportDownload } from "@/components/hr/hr-report-download";

const fieldClass =
  "min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100";

const statusLabels: Record<EmploymentStatus, string> = {
  ACTIVE: "Đang làm việc",
  INACTIVE: "Tạm ngưng",
  ON_LEAVE: "Đang nghỉ phép",
  TERMINATED: "Đã nghỉ việc",
};

function salary(value: string | null) {
  if (!value) return "Chưa thiết lập";
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(Number(value));
}

export function EmployeeWorkspace() {
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [employmentStatus, setEmploymentStatus] = useState<
    EmploymentStatus | ""
  >("");
  const [creating, setCreating] = useState(false);
  const [accountSearch, setAccountSearch] = useState("");
  const [accountQuery, setAccountQuery] = useState("");
  const [selectedUserId, setSelectedUserId] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [invitedEmail, setInvitedEmail] = useState("");
  const [editing, setEditing] = useState<Employee | null>(null);
  const [editForm, setEditForm] = useState({
    userId: "",
    email: "",
    departmentId: "",
    position: "",
    employmentStatus: "ACTIVE" as EmploymentStatus,
    contractType: "",
    baseSalary: "",
  });
  const [form, setForm] = useState({
    employeeCode: "",
    fullName: "",
    email: "",
    phone: "",
    departmentId: "",
    position: "",
    joinDate: "",
    contractType: "FULL_TIME",
    baseSalary: "",
  });

  const departments = useQuery({
    queryKey: ["hr", "departments", "options"],
    queryFn: () => hrDepartmentApi.list({ pageSize: 100 }),
  });
  const employees = useQuery({
    queryKey: ["hr", "employees", search, departmentId, employmentStatus],
    queryFn: () =>
      hrEmployeeApi.list({
        search: search || undefined,
        departmentId: departmentId || undefined,
        employmentStatus: employmentStatus || undefined,
        pageSize: 100,
      }),
  });
  const accounts = useQuery({
    queryKey: ["hr", "available-user-accounts", accountQuery],
    queryFn: () =>
      adminUsersApi.list({
        search: accountQuery,
        status: "ACTIVE",
        verified: true,
        pageSize: 100,
      }),
    enabled:
      Boolean(accountQuery) &&
      (creating || Boolean(editing && !editing.userId)),
  });
  const createEmployee = useMutation({
    mutationFn: () =>
      hrEmployeeApi.create({
        ...form,
        userId: selectedUserId || null,
        phone: form.phone || null,
        contractType: form.contractType || null,
        baseSalary: form.baseSalary || null,
      }),
    onSuccess: () => {
      setCreating(false);
      setSelectedUserId("");
      setForm({
        employeeCode: "",
        fullName: "",
        email: "",
        phone: "",
        departmentId: "",
        position: "",
        joinDate: "",
        contractType: "FULL_TIME",
        baseSalary: "",
      });
      void queryClient.invalidateQueries({ queryKey: ["hr", "employees"] });
    },
  });
  const inviteEmployee = useMutation({
    mutationFn: () => employeeInvitationsApi.create(inviteEmail.trim()),
    onSuccess: () => {
      setInvitedEmail(inviteEmail.trim());
      setInviteEmail("");
    },
  });
  const updateEmployee = useMutation({
    mutationFn: () => {
      if (!editing) throw new Error("Missing employee edit target");
      return hrEmployeeApi.update(editing.id, {
        ...(editing.userId
          ? {}
          : { userId: editForm.userId || null, email: editForm.email }),
        departmentId: editForm.departmentId,
        position: editForm.position.trim(),
        employmentStatus: editForm.employmentStatus,
        contractType: editForm.contractType || null,
        baseSalary: editForm.baseSalary || null,
      });
    },
    onSuccess: () => {
      setEditing(null);
      void queryClient.invalidateQueries({ queryKey: ["hr", "employees"] });
    },
  });
  const rows = employees.data?.data ?? [];

  function updateField(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setSearch(searchDraft.trim());
  }

  function beginEdit(employee: Employee) {
    setEditing(employee);
    setEditForm({
      userId: employee.userId || "",
      email: employee.email,
      departmentId: employee.departmentId,
      position: employee.position,
      employmentStatus: employee.employmentStatus,
      contractType: employee.contractType ?? "",
      baseSalary: employee.baseSalary ?? "",
    });
  }

  return (
    <section
      className="mx-auto max-w-7xl space-y-6 pb-12"
      aria-labelledby="employees-title"
    >
      <header className="relative overflow-hidden rounded-3xl border border-neutral-800 bg-neutral-950 px-6 py-7 text-white sm:px-8">
        <div className="absolute inset-y-0 right-0 w-2/5 bg-[radial-gradient(circle_at_center,rgba(34,197,94,0.2),transparent_68%)]" />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-emerald-300">
              <BriefcaseBusiness className="size-4" aria-hidden="true" /> Hồ sơ
              nội bộ
            </p>
            <h1
              id="employees-title"
              className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
            >
              Đội ngũ nhân sự
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-300">
              Một nguồn dữ liệu rõ ràng cho cơ cấu, vị trí, trạng thái làm việc
              và thông tin hợp đồng.
            </p>
          </div>
          <button
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-emerald-400 px-5 text-sm font-bold text-neutral-950 transition hover:bg-emerald-300 active:scale-[0.98]"
            onClick={() => setCreating(true)}
            type="button"
          >
            <Plus className="size-4" /> Thêm nhân viên
          </button>
        </div>
      </header>

      <form
        className="grid gap-3 rounded-2xl border border-neutral-200 bg-white p-4 md:grid-cols-[1fr_14rem_12rem_auto]"
        onSubmit={submitSearch}
      >
        <label className="text-sm font-bold text-neutral-800">
          Tìm kiếm
          <span className="relative mt-2 block">
            <Search className="absolute left-3 top-3.5 size-4 text-neutral-400" />
            <input
              className={`${fieldClass} pl-10`}
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="Tên, email hoặc mã nhân viên"
              value={searchDraft}
            />
          </span>
        </label>
        <label className="text-sm font-bold text-neutral-800">
          Phòng ban
          <select
            className={`${fieldClass} mt-2`}
            onChange={(event) => setDepartmentId(event.target.value)}
            value={departmentId}
          >
            <option value="">Tất cả phòng ban</option>
            {departments.data?.data.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-bold text-neutral-800">
          Trạng thái
          <select
            className={`${fieldClass} mt-2`}
            onChange={(event) =>
              setEmploymentStatus(event.target.value as EmploymentStatus | "")
            }
            value={employmentStatus}
          >
            <option value="">Tất cả</option>
            {Object.entries(statusLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <button
          className="min-h-11 self-end rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white transition hover:bg-neutral-800"
          type="submit"
        >
          Áp dụng
        </button>
      </form>

      <HrReportDownload
        download={() =>
          hrEmployeeApi.exportXlsx({
            search: search || undefined,
            departmentId: departmentId || undefined,
            employmentStatus: employmentStatus || undefined,
          })
        }
        errorMessage="Không thể tải báo cáo nhân viên."
        filename="hr-employees.xlsx"
      />

      {creating ? (
        <div className="space-y-4">
          <form
            className="grid gap-3 rounded-2xl border border-emerald-200 bg-white p-5 sm:grid-cols-[1fr_auto] sm:items-end"
            onSubmit={(event) => {
              event.preventDefault();
              inviteEmployee.mutate();
            }}
          >
            <label className="text-sm font-bold text-neutral-800">
              Mời nhân viên qua Gmail
              <input
                className={`${fieldClass} mt-2`}
                onChange={(event) => setInviteEmail(event.target.value)}
                placeholder="ten.nhan.vien@gmail.com"
                required
                type="email"
                value={inviteEmail}
              />
            </label>
            <button
              className="min-h-11 rounded-xl bg-emerald-600 px-5 text-sm font-bold text-white disabled:opacity-50"
              disabled={inviteEmployee.isPending}
              type="submit"
            >
              {inviteEmployee.isPending ? "Đang gửi…" : "Gửi lời mời"}
            </button>
            <p className="text-xs leading-5 text-neutral-600 sm:col-span-2">
              Người nhận xác minh Gmail để kích hoạt tài khoản USER. Sau đó,
              chọn tài khoản trong danh sách bên dưới và cấu hình hồ sơ nhân sự.
            </p>
            {invitedEmail ? (
              <p
                className="text-sm font-semibold text-emerald-800 sm:col-span-2"
                role="status"
              >
                Đã tạo lời mời cho {invitedEmail}. Email sẽ được gửi qua hệ
                thống thông báo.
              </p>
            ) : null}
            {inviteEmployee.error ? (
              <p className="text-sm text-red-700 sm:col-span-2" role="alert">
                {inviteEmployee.error instanceof ApiError
                  ? inviteEmployee.error.message
                  : "Không thể gửi lời mời. Vui lòng thử lại."}
              </p>
            ) : null}
          </form>
          <form
            className="hr-employee-form grid gap-4 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 md:grid-cols-2 xl:grid-cols-3"
            onSubmit={(event) => {
              event.preventDefault();
              createEmployee.mutate();
            }}
          >
            <div className="rounded-xl border border-current/15 p-4 md:col-span-2 xl:col-span-3">
              <label className="text-sm font-bold text-neutral-800">
                Tìm tài khoản đã đăng ký
                <input
                  className={`${fieldClass} mt-2`}
                  onChange={(event) => setAccountSearch(event.target.value)}
                  placeholder="Tên hoặc email người dùng"
                  value={accountSearch}
                />
              </label>
              <button
                className="mt-2 min-h-10 rounded-lg border border-neutral-300 px-4 text-sm font-semibold"
                disabled={accountSearch.trim().length < 2}
                onClick={() => {
                  setSelectedUserId("");
                  setAccountQuery(accountSearch.trim());
                }}
                type="button"
              >
                Tìm tài khoản
              </button>
              {accounts.isPending && accountQuery ? (
                <p className="mt-2 text-xs text-neutral-600" role="status">
                  Đang tìm tài khoản…
                </p>
              ) : null}
              {accounts.isError ? (
                <p className="mt-2 text-xs text-red-600" role="alert">
                  Không tải được danh sách tài khoản. Vui lòng tìm lại.
                </p>
              ) : null}
              <label className="mt-3 block text-sm font-bold text-neutral-800">
                Liên kết tài khoản
                <select
                  className={`${fieldClass} mt-2`}
                  onChange={(event) => {
                    const user = accounts.data?.data.find(
                      (item) => item.id === event.target.value,
                    );
                    setSelectedUserId(event.target.value);
                    if (user)
                      setForm((current) => ({
                        ...current,
                        fullName: user.fullName || current.fullName,
                        email: user.email,
                      }));
                  }}
                  value={selectedUserId}
                >
                  <option value="">
                    Chưa liên kết — nhập email để lập hồ sơ
                  </option>
                  {accounts.data?.data
                    .filter(
                      (user) =>
                        user.isEmailVerified &&
                        user.roles.includes("USER") &&
                        !rows.some((employee) => employee.userId === user.id),
                    )
                    .map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.fullName || user.email} · {user.email}
                      </option>
                    ))}
                </select>
              </label>
              <p className="mt-2 text-xs text-neutral-600">
                Chọn tài khoản USER đã xác minh, hoặc gửi lời mời Gmail ở phía
                trên rồi liên kết khi nhân viên xác nhận. Lập hồ sơ bằng email
                không tự gửi lời mời.
              </p>
            </div>
            <div className="flex items-start justify-between md:col-span-2 xl:col-span-3">
              <div>
                <h2 className="text-lg font-bold text-neutral-950">
                  Hồ sơ nhân viên mới
                </h2>
                <p className="mt-1 text-sm text-neutral-600">
                  Thông tin lương chỉ hiển thị trong khu vực quản trị được bảo
                  vệ.
                </p>
              </div>
              <button
                aria-label="Đóng biểu mẫu"
                className="rounded-lg p-2 text-neutral-600 hover:bg-white"
                onClick={() => setCreating(false)}
                type="button"
              >
                <X className="size-5" />
              </button>
            </div>
            <label className="text-sm font-bold text-neutral-800">
              Mã nhân viên
              <input
                className={`${fieldClass} mt-2`}
                onChange={(e) => updateField("employeeCode", e.target.value)}
                required
                value={form.employeeCode}
              />
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Họ và tên
              <input
                className={`${fieldClass} mt-2`}
                onChange={(e) => updateField("fullName", e.target.value)}
                required
                value={form.fullName}
              />
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Email
              <input
                className={`${fieldClass} mt-2`}
                onChange={(e) => updateField("email", e.target.value)}
                readOnly={Boolean(selectedUserId)}
                required
                type="email"
                value={form.email}
              />
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Điện thoại
              <input
                className={`${fieldClass} mt-2`}
                onChange={(e) => updateField("phone", e.target.value)}
                value={form.phone}
              />
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Phòng ban
              <select
                className={`${fieldClass} mt-2`}
                onChange={(e) => updateField("departmentId", e.target.value)}
                required
                value={form.departmentId}
              >
                <option value="">Chọn phòng ban</option>
                {departments.data?.data.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Vị trí
              <input
                className={`${fieldClass} mt-2`}
                onChange={(e) => updateField("position", e.target.value)}
                required
                value={form.position}
              />
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Ngày vào làm
              <input
                className={`${fieldClass} mt-2`}
                onChange={(e) => updateField("joinDate", e.target.value)}
                required
                type="date"
                value={form.joinDate}
              />
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Loại hợp đồng
              <select
                className={`${fieldClass} mt-2`}
                onChange={(e) => updateField("contractType", e.target.value)}
                value={form.contractType}
              >
                <option value="FULL_TIME">Toàn thời gian</option>
                <option value="PART_TIME">Bán thời gian</option>
                <option value="PROBATION">Thử việc</option>
                <option value="CONTRACTOR">Cộng tác</option>
              </select>
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Lương cơ bản
              <input
                className={`${fieldClass} mt-2`}
                min="0"
                onChange={(e) => updateField("baseSalary", e.target.value)}
                step="1000"
                type="number"
                value={form.baseSalary}
              />
            </label>
            {createEmployee.error ? (
              <p className="text-sm font-semibold text-red-700 md:col-span-2 xl:col-span-3">
                {createEmployee.error instanceof ApiError
                  ? createEmployee.error.message
                  : "Không thể tạo nhân viên."}
              </p>
            ) : null}
            <div className="flex justify-end md:col-span-2 xl:col-span-3">
              <button
                className="min-h-11 rounded-xl bg-neutral-950 px-6 text-sm font-bold text-white disabled:opacity-50"
                disabled={createEmployee.isPending}
                type="submit"
              >
                {createEmployee.isPending ? "Đang lưu..." : "Tạo hồ sơ"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {editing ? (
        <form
          className="hr-employee-form grid gap-4 rounded-2xl border border-neutral-300 bg-white p-5 shadow-[0_18px_50px_rgba(15,23,42,0.08)] md:grid-cols-2 xl:grid-cols-3"
          onSubmit={(event) => {
            event.preventDefault();
            const statusChanged =
              editing.employmentStatus !== editForm.employmentStatus;
            if (
              !statusChanged ||
              window.confirm(
                "Xác nhận thay đổi trạng thái làm việc của nhân viên?",
              )
            )
              updateEmployee.mutate();
          }}
        >
          {!editing.userId ? (
            <div className="rounded-xl border border-current/15 p-4 md:col-span-2 xl:col-span-3">
              <label className="text-sm font-bold text-neutral-800">
                Tìm tài khoản USER để liên kết
                <input
                  className={`${fieldClass} mt-2`}
                  onChange={(event) => setAccountSearch(event.target.value)}
                  placeholder="Tên hoặc email"
                  value={accountSearch}
                />
              </label>
              <button
                className="mt-2 min-h-10 rounded-lg border border-neutral-300 px-4 text-sm font-semibold"
                disabled={accountSearch.trim().length < 2}
                onClick={() => {
                  setEditForm((current) => ({
                    ...current,
                    userId: "",
                    email: editing.email,
                  }));
                  setAccountQuery(accountSearch.trim());
                }}
                type="button"
              >
                Tìm tài khoản
              </button>
              {accounts.isError ? (
                <p className="mt-2 text-xs text-red-600" role="alert">
                  Không tải được danh sách tài khoản. Vui lòng tìm lại.
                </p>
              ) : null}
              <label className="mt-3 block text-sm font-bold text-neutral-800">
                Tài khoản
                <select
                  className={`${fieldClass} mt-2`}
                  onChange={(event) => {
                    const user = accounts.data?.data.find(
                      (item) => item.id === event.target.value,
                    );
                    setEditForm((current) => ({
                      ...current,
                      userId: event.target.value,
                      email: user?.email || editing.email,
                    }));
                  }}
                  value={editForm.userId}
                >
                  <option value="">Chưa liên kết</option>
                  {accounts.data?.data
                    .filter(
                      (user) =>
                        user.isEmailVerified &&
                        user.roles.includes("USER") &&
                        !rows.some((employee) => employee.userId === user.id),
                    )
                    .map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.fullName || user.email} · {user.email}
                      </option>
                    ))}
                </select>
              </label>
              <p className="mt-2 text-xs text-neutral-600">
                Email hồ sơ sẽ được đồng bộ với tài khoản đã xác minh. Không thể
                chuyển liên kết sang tài khoản khác sau khi lưu.
              </p>
            </div>
          ) : null}
          <div className="flex items-start justify-between md:col-span-2 xl:col-span-3">
            <div>
              <h2 className="text-lg font-bold text-neutral-950">
                Cập nhật {editing.fullName}
              </h2>
              <p className="mt-1 text-sm text-neutral-600">
                {editing.employeeCode} · Các thay đổi quan trọng được ghi vào
                audit log.
              </p>
            </div>
            <button
              aria-label="Đóng biểu mẫu chỉnh sửa"
              className="rounded-lg p-2 text-neutral-600 hover:bg-neutral-100"
              onClick={() => setEditing(null)}
              type="button"
            >
              <X className="size-5" />
            </button>
          </div>
          <label className="text-sm font-bold text-neutral-800">
            Phòng ban
            <select
              className={`${fieldClass} mt-2`}
              onChange={(e) =>
                setEditForm((current) => ({
                  ...current,
                  departmentId: e.target.value,
                }))
              }
              required
              value={editForm.departmentId}
            >
              {departments.data?.data.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-bold text-neutral-800">
            Vị trí
            <input
              className={`${fieldClass} mt-2`}
              onChange={(e) =>
                setEditForm((current) => ({
                  ...current,
                  position: e.target.value,
                }))
              }
              required
              value={editForm.position}
            />
          </label>
          <label className="text-sm font-bold text-neutral-800">
            Trạng thái
            <select
              className={`${fieldClass} mt-2`}
              onChange={(e) =>
                setEditForm((current) => ({
                  ...current,
                  employmentStatus: e.target.value as EmploymentStatus,
                }))
              }
              value={editForm.employmentStatus}
            >
              {Object.entries(statusLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-bold text-neutral-800">
            Loại hợp đồng
            <select
              className={`${fieldClass} mt-2`}
              onChange={(e) =>
                setEditForm((current) => ({
                  ...current,
                  contractType: e.target.value,
                }))
              }
              value={editForm.contractType}
            >
              <option value="">Chưa xác định</option>
              <option value="FULL_TIME">Toàn thời gian</option>
              <option value="PART_TIME">Bán thời gian</option>
              <option value="PROBATION">Thử việc</option>
              <option value="CONTRACTOR">Cộng tác</option>
            </select>
          </label>
          <label className="text-sm font-bold text-neutral-800">
            Lương cơ bản
            <input
              className={`${fieldClass} mt-2`}
              min="0"
              onChange={(e) =>
                setEditForm((current) => ({
                  ...current,
                  baseSalary: e.target.value,
                }))
              }
              step="1000"
              type="number"
              value={editForm.baseSalary}
            />
          </label>
          {updateEmployee.error ? (
            <p className="self-end text-sm font-semibold text-red-700">
              {updateEmployee.error instanceof ApiError
                ? updateEmployee.error.message
                : "Không thể cập nhật nhân viên."}
            </p>
          ) : null}
          <div className="flex justify-end md:col-span-2 xl:col-span-3">
            <button
              className="min-h-11 rounded-xl bg-neutral-950 px-6 text-sm font-bold text-white disabled:opacity-50"
              disabled={updateEmployee.isPending}
              type="submit"
            >
              {updateEmployee.isPending ? "Đang cập nhật..." : "Lưu thay đổi"}
            </button>
          </div>
        </form>
      ) : null}

      <div className="overflow-x-auto rounded-2xl border border-neutral-200 bg-white">
        <table className="min-w-[980px] w-full text-left">
          <thead className="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th className="px-5 py-3">Nhân viên</th>
              <th className="px-5 py-3">Phòng ban</th>
              <th className="px-5 py-3">Vị trí</th>
              <th className="px-5 py-3">Trạng thái</th>
              <th className="px-5 py-3 text-right">Lương cơ bản</th>
              <th aria-label="Thao tác" className="px-5 py-3" />
            </tr>
          </thead>
          <tbody>
            {employees.isPending ? (
              <tr>
                <td className="p-5" colSpan={6}>
                  <div className="h-14 animate-pulse rounded-xl bg-neutral-100" />
                </td>
              </tr>
            ) : null}
            {employees.isError ? (
              <tr>
                <td className="p-8 text-center" colSpan={6}>
                  <p className="font-bold">
                    Không tải được danh sách nhân viên
                  </p>
                  <button
                    className="mt-3 text-sm font-bold text-primary-700"
                    onClick={() => void employees.refetch()}
                    type="button"
                  >
                    Thử lại
                  </button>
                </td>
              </tr>
            ) : null}
            {!employees.isPending && !employees.isError && rows.length === 0 ? (
              <tr>
                <td className="p-10 text-center" colSpan={6}>
                  <UserRoundPlus className="mx-auto size-9 text-neutral-400" />
                  <p className="mt-3 font-bold text-neutral-950">
                    Chưa có nhân viên phù hợp
                  </p>
                  <p className="mt-1 text-sm text-neutral-600">
                    Thêm hồ sơ mới hoặc thay đổi bộ lọc.
                  </p>
                </td>
              </tr>
            ) : null}
            {rows.map((employee) => (
              <tr className="border-t border-neutral-100" key={employee.id}>
                <td className="px-5 py-4">
                  <p className="font-bold text-neutral-950">
                    {employee.fullName}
                  </p>
                  <p className="mt-1 text-xs text-neutral-500">
                    {employee.employeeCode} · {employee.email}
                  </p>
                </td>
                <td className="px-5 py-4 text-sm text-neutral-700">
                  {employee.departmentName}
                </td>
                <td className="px-5 py-4 text-sm text-neutral-700">
                  {employee.position}
                </td>
                <td className="px-5 py-4">
                  <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-800">
                    {statusLabels[employee.employmentStatus]}
                  </span>
                </td>
                <td className="px-5 py-4 text-right font-mono text-sm font-bold text-neutral-800">
                  {salary(employee.baseSalary)}
                </td>
                <td className="px-5 py-4">
                  <button
                    className="min-h-9 rounded-lg border border-neutral-300 px-3 text-xs font-bold text-neutral-800 hover:bg-neutral-50"
                    onClick={() => beginEdit(employee)}
                    type="button"
                  >
                    Chỉnh sửa
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
