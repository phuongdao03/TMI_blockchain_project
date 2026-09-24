"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Pencil, Plus, Search, Sparkles, X } from "lucide-react";
import { type FormEvent, useState } from "react";

import { ApiError, hrDepartmentApi } from "@/lib/api/client";
import { HrReportDownload } from "@/components/hr/hr-report-download";
import type { Department } from "@/lib/api/types";

const fieldClass =
  "min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100";

export function DepartmentWorkspace() {
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [editing, setEditing] = useState<Department | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const departments = useQuery({
    queryKey: ["hr", "departments", search],
    queryFn: () =>
      hrDepartmentApi.list({ search: search || undefined, pageSize: 100 }),
  });
  const createDepartment = useMutation({
    mutationFn: () =>
      hrDepartmentApi.create({
        code: code.trim(),
        name: name.trim(),
        description: description.trim() || null,
      }),
    onSuccess: () => {
      setCreating(false);
      setCode("");
      setName("");
      setDescription("");
      void queryClient.invalidateQueries({ queryKey: ["hr", "departments"] });
    },
  });
  const rows = departments.data?.data ?? [];
  const updateDepartment = useMutation({
    mutationFn: () =>
      hrDepartmentApi.update(editing!.id, {
        name: editName.trim(),
        description: editDescription.trim() || null,
      }),
    onSuccess: () => {
      setEditing(null);
      void queryClient.invalidateQueries({ queryKey: ["hr", "departments"] });
    },
  });

  function startEdit(department: Department) {
    setEditing(department);
    setEditName(department.name);
    setEditDescription(department.description ?? "");
    updateDepartment.reset();
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setSearch(searchDraft.trim());
  }

  function submitCreate(event: FormEvent) {
    event.preventDefault();
    createDepartment.mutate();
  }

  return (
    <section
      className="mx-auto max-w-7xl space-y-6 pb-12"
      aria-labelledby="departments-title"
    >
      <header className="relative overflow-hidden rounded-3xl border border-neutral-800 bg-neutral-950 px-6 py-7 text-white sm:px-8">
        <div className="absolute inset-y-0 right-0 w-2/5 bg-[radial-gradient(circle_at_center,rgba(34,197,94,0.18),transparent_68%)]" />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-emerald-300">
              <Sparkles className="size-4" aria-hidden="true" /> Không gian nhân
              sự
            </p>
            <h1
              id="departments-title"
              className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
            >
              Cơ cấu phòng ban
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-300">
              Tổ chức đội ngũ bằng dữ liệu nhất quán, sẵn sàng liên kết nhân
              viên và báo cáo vận hành.
            </p>
          </div>
          <button
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-emerald-400 px-5 text-sm font-bold text-neutral-950 transition hover:bg-emerald-300 active:scale-[0.98]"
            onClick={() => setCreating(true)}
            type="button"
          >
            <Plus className="size-4" aria-hidden="true" /> Thêm phòng ban
          </button>
        </div>
      </header>

      <form className="flex flex-col gap-3 sm:flex-row" onSubmit={submitSearch}>
        <label className="relative flex-1">
          <span className="sr-only">Tìm phòng ban</span>
          <Search
            className="absolute left-4 top-3.5 size-4 text-neutral-400"
            aria-hidden="true"
          />
          <input
            className={`${fieldClass} pl-11`}
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            placeholder="Tìm theo tên hoặc mã phòng ban"
          />
        </label>
        <button
          className="min-h-11 rounded-xl border border-neutral-300 bg-white px-5 text-sm font-bold text-neutral-900 transition hover:bg-neutral-50"
          type="submit"
        >
          Tìm kiếm
        </button>
      </form>

      <HrReportDownload
        download={() =>
          hrDepartmentApi.exportXlsx({ search: search || undefined })
        }
        errorMessage="Không thể tải báo cáo phòng ban."
        filename="hr-departments.xlsx"
      />

      {creating ? (
        <form
          className="hr-department-form grid gap-4 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 md:grid-cols-2"
          onSubmit={submitCreate}
        >
          <div className="flex items-center justify-between md:col-span-2">
            <div>
              <h2 className="text-lg font-bold text-neutral-950">
                Phòng ban mới
              </h2>
              <p className="mt-1 text-sm text-neutral-600">
                Mã phòng ban là duy nhất và sẽ được chuẩn hóa thành chữ in hoa.
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
            Mã phòng ban
            <input
              className={`${fieldClass} mt-2`}
              maxLength={32}
              onChange={(e) => setCode(e.target.value)}
              required
              value={code}
            />
          </label>
          <label className="text-sm font-bold text-neutral-800">
            Tên phòng ban
            <input
              className={`${fieldClass} mt-2`}
              maxLength={160}
              onChange={(e) => setName(e.target.value)}
              required
              value={name}
            />
          </label>
          <label className="text-sm font-bold text-neutral-800 md:col-span-2">
            Mô tả
            <textarea
              className={`${fieldClass} mt-2 min-h-24 py-3`}
              maxLength={2000}
              onChange={(e) => setDescription(e.target.value)}
              value={description}
            />
          </label>
          {createDepartment.error ? (
            <p className="text-sm font-semibold text-red-700 md:col-span-2">
              {createDepartment.error instanceof ApiError
                ? createDepartment.error.message
                : "Không thể tạo phòng ban."}
            </p>
          ) : null}
          <div className="flex justify-end md:col-span-2">
            <button
              className="min-h-11 rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white disabled:opacity-50"
              disabled={createDepartment.isPending}
              type="submit"
            >
              {createDepartment.isPending ? "Đang lưu..." : "Lưu phòng ban"}
            </button>
          </div>
        </form>
      ) : null}

      {editing ? (
        <form
          className="hr-department-form grid gap-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 dark:border-emerald-900 dark:bg-emerald-950/30 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            updateDepartment.mutate();
          }}
        >
          <div className="flex items-center justify-between sm:col-span-2">
            <h2 className="text-base font-bold text-neutral-950 dark:text-white">
              Chỉnh sửa phòng ban · {editing.code}
            </h2>
            <button
              aria-label="Đóng chỉnh sửa"
              className="rounded-lg p-2 dark:text-white"
              onClick={() => setEditing(null)}
              type="button"
            >
              <X className="size-5" />
            </button>
          </div>
          <label className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            Tên phòng ban
            <input
              className={`${fieldClass} mt-2`}
              maxLength={160}
              minLength={2}
              onChange={(event) => setEditName(event.target.value)}
              required
              value={editName}
            />
          </label>
          <label className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            Mô tả
            <input
              className={`${fieldClass} mt-2`}
              maxLength={2000}
              onChange={(event) => setEditDescription(event.target.value)}
              value={editDescription}
            />
          </label>
          {updateDepartment.isError ? (
            <p
              className="text-sm font-semibold text-red-700 dark:text-red-300 sm:col-span-2"
              role="alert"
            >
              {updateDepartment.error instanceof ApiError
                ? updateDepartment.error.message
                : "Không thể cập nhật phòng ban."}
            </p>
          ) : null}
          <div className="flex justify-end sm:col-span-2">
            <button
              className="min-h-11 rounded-xl bg-emerald-700 px-5 text-sm font-bold text-white disabled:opacity-50"
              disabled={updateDepartment.isPending}
              type="submit"
            >
              {updateDepartment.isPending ? "Đang lưu..." : "Lưu thay đổi"}
            </button>
          </div>
        </form>
      ) : null}

      <div className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div className="grid grid-cols-[6rem_1fr_auto] gap-4 border-b border-neutral-200 bg-neutral-50 px-5 py-3 text-xs font-bold uppercase tracking-wide text-neutral-500 sm:grid-cols-[7rem_1fr_2fr_auto]">
          <span>Mã</span>
          <span>Phòng ban</span>
          <span className="hidden sm:block">Mô tả</span>
          <span>Trạng thái</span>
        </div>
        {departments.isPending ? (
          <div className="space-y-3 p-5" aria-label="Đang tải">
            <div className="h-12 animate-pulse rounded-xl bg-neutral-100" />
            <div className="h-12 animate-pulse rounded-xl bg-neutral-100" />
          </div>
        ) : null}
        {departments.isError ? (
          <div className="p-8 text-center">
            <p className="font-bold text-neutral-900">
              Không tải được phòng ban
            </p>
            <button
              className="mt-3 text-sm font-bold text-primary-700"
              onClick={() => void departments.refetch()}
              type="button"
            >
              Thử lại
            </button>
          </div>
        ) : null}
        {!departments.isPending && !departments.isError && rows.length === 0 ? (
          <div className="p-10 text-center">
            <Building2 className="mx-auto size-9 text-neutral-400" />
            <p className="mt-3 font-bold text-neutral-950">Chưa có phòng ban</p>
            <p className="mt-1 text-sm text-neutral-600">
              Tạo phòng ban đầu tiên để bắt đầu cấu trúc đội ngũ.
            </p>
          </div>
        ) : null}
        {rows.map((department) => (
          <article
            className="grid grid-cols-[6rem_1fr_auto] gap-4 border-b border-neutral-100 px-5 py-4 last:border-0 sm:grid-cols-[7rem_1fr_2fr_auto]"
            key={department.id}
          >
            <span className="font-mono text-sm font-bold text-emerald-700">
              {department.code}
            </span>
            <span className="text-sm font-bold text-neutral-950">
              {department.name}
            </span>
            <span className="hidden text-sm text-neutral-600 sm:block">
              {department.description || "Chưa có mô tả"}
            </span>
            <span className="flex flex-col items-end gap-2">
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-800">
                Hoạt động
              </span>
              <button
                aria-label={`Sửa phòng ban ${department.name}`}
                className="inline-flex min-h-9 items-center gap-1 rounded-lg border border-neutral-300 px-2 text-xs font-semibold text-neutral-800 hover:bg-neutral-50"
                onClick={() => startEdit(department)}
                type="button"
              >
                <Pencil aria-hidden="true" className="size-3.5" /> Sửa
              </button>
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}
