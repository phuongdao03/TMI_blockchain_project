"use client";

import {
  Building2,
  CircleAlert,
  LoaderCircle,
  Pencil,
  Plus,
  Power,
} from "lucide-react";
import { type FormEvent, useState } from "react";

import type { AttendanceWorksite } from "@/lib/api/types";

import type { WorksiteInput } from "./attendance-configuration-types";

const fieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100";

type WorksiteQuery = {
  data?: { data: AttendanceWorksite[]; meta: { total: number } };
  isPending: boolean;
  isError: boolean;
};

export function AttendanceWorksitePanel({
  isCreating,
  isUpdating,
  onCreate,
  onRetry,
  onSelect,
  onRename,
  onToggleActive,
  selectedWorksiteId,
  worksites,
}: {
  isCreating: boolean;
  isUpdating: boolean;
  onCreate: (input: WorksiteInput) => Promise<unknown>;
  onRetry: () => void;
  onSelect: (worksiteId: string) => void;
  onRename: (worksite: AttendanceWorksite, name: string) => Promise<unknown>;
  onToggleActive: (worksite: AttendanceWorksite) => Promise<unknown>;
  selectedWorksiteId: string | null;
  worksites: WorksiteQuery;
}) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const items = worksites.data?.data ?? [];

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    if (!code.trim() || !name.trim()) {
      setFormError("Nhập mã và tên trước khi tạo điểm chấm công.");
      return;
    }
    try {
      await onCreate({ code: code.trim(), name: name.trim() });
      setCode("");
      setName("");
    } catch {
      setFormError("Không thể tạo điểm chấm công. Kiểm tra mã và thử lại.");
    }
  }

  async function toggle(worksite: AttendanceWorksite) {
    const nextState = worksite.status === "ACTIVE" ? "tạm ngưng" : "kích hoạt";
    if (!window.confirm(`Xác nhận ${nextState} ${worksite.name}?`)) return;
    setFormError(null);
    try {
      await onToggleActive(worksite);
    } catch {
      setFormError("Không thể cập nhật trạng thái điểm chấm công.");
    }
  }

  async function rename(worksite: AttendanceWorksite) {
    const nextName = editingName.trim();
    if (nextName.length < 2) {
      setFormError("Tên địa điểm cần ít nhất 2 ký tự.");
      return;
    }
    try {
      await onRename(worksite, nextName);
      setEditingId(null);
      setFormError(null);
    } catch {
      setFormError("Không thể đổi tên địa điểm. Vui lòng thử lại.");
    }
  }

  return (
    <section
      aria-labelledby="attendance-worksites-title"
      className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm sm:p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            01 · Địa điểm
          </p>
          <h2
            className="mt-1 text-xl font-bold text-neutral-950"
            id="attendance-worksites-title"
          >
            Điểm chấm công
          </h2>
          <p className="mt-1 text-sm leading-6 text-neutral-600">
            Mỗi mã đại diện cho một nơi làm việc có thể có nhiều chính sách theo
            thời gian.
          </p>
        </div>
        <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs font-bold text-neutral-700">
          {worksites.data?.meta.total ?? 0} địa điểm
        </span>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <form className="rounded-2xl bg-neutral-50 p-4" onSubmit={submit}>
          <h3 className="text-sm font-bold text-neutral-950">
            Tạo địa điểm mới
          </h3>
          <label
            className="mt-4 block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-worksite-code"
          >
            Mã điểm chấm công
            <input
              className={fieldClass}
              id="attendance-worksite-code"
              maxLength={32}
              onChange={(event) => setCode(event.target.value)}
              placeholder="VD: SGN-HQ"
              value={code}
            />
          </label>
          <label
            className="mt-3 block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-worksite-name"
          >
            Tên điểm chấm công
            <input
              className={fieldClass}
              id="attendance-worksite-name"
              maxLength={160}
              onChange={(event) => setName(event.target.value)}
              placeholder="VD: Văn phòng TP. Hồ Chí Minh"
              value={name}
            />
          </label>
          {formError ? (
            <p className="mt-3 flex gap-2 text-sm text-rose-700" role="alert">
              <CircleAlert
                aria-hidden="true"
                className="mt-0.5 size-4 shrink-0"
              />
              {formError}
            </p>
          ) : null}
          <button
            className="mt-4 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-neutral-950 px-4 text-sm font-bold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isCreating}
            type="submit"
          >
            {isCreating ? (
              <LoaderCircle
                aria-hidden="true"
                className="size-4 animate-spin"
              />
            ) : (
              <Plus aria-hidden="true" className="size-4" />
            )}
            Tạo điểm chấm công
          </button>
        </form>

        <div aria-live="polite" className="min-w-0">
          {worksites.isPending ? <WorksiteSkeleton /> : null}
          {worksites.isError ? (
            <div
              className="rounded-xl border border-rose-100 bg-rose-50 p-4 text-sm text-rose-800"
              role="alert"
            >
              Không thể tải điểm chấm công.
              <button
                className="ml-2 font-bold underline"
                onClick={onRetry}
                type="button"
              >
                Thử lại
              </button>
            </div>
          ) : null}
          {!worksites.isPending && !worksites.isError && items.length === 0 ? (
            <div className="flex min-h-44 flex-col items-center justify-center rounded-2xl border border-dashed border-neutral-300 p-5 text-center">
              <Building2
                aria-hidden="true"
                className="size-7 text-neutral-400"
              />
              <p className="mt-3 text-sm font-bold text-neutral-800">
                Chưa có điểm chấm công
              </p>
              <p className="mt-1 text-sm text-neutral-600">
                Tạo địa điểm đầu tiên ở biểu mẫu bên trái.
              </p>
            </div>
          ) : null}
          <ul className="grid gap-3 sm:grid-cols-2" role="list">
            {items.map((worksite) => {
              const selected = worksite.id === selectedWorksiteId;
              const isActive = worksite.status === "ACTIVE";
              return (
                <li key={worksite.id}>
                  <div
                    className={`hr-worksite-card rounded-2xl border p-4 transition ${selected ? "border-primary-500 bg-primary-50/60 ring-2 ring-primary-100" : "border-neutral-200 bg-white hover:border-neutral-300"}`}
                  >
                    <button
                      className="block w-full text-left"
                      onClick={() => onSelect(worksite.id)}
                      type="button"
                    >
                      <span className="text-xs font-bold tracking-wider text-primary-700">
                        {worksite.code}
                      </span>
                      <span className="mt-1 block text-sm font-bold text-neutral-950">
                        {worksite.name}
                      </span>
                    </button>
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-bold ${isActive ? "bg-emerald-50 text-emerald-700" : "bg-neutral-100 text-neutral-600"}`}
                      >
                        {isActive ? "Đang hoạt động" : "Tạm ngưng"}
                      </span>
                      <div className="flex flex-wrap gap-2">
                      <button
                        aria-label={`Đổi tên ${worksite.name}`}
                        className="inline-flex min-h-10 items-center justify-center gap-1 rounded-lg border border-neutral-200 px-2 text-xs font-semibold text-neutral-700 hover:text-neutral-950"
                        onClick={() => { setEditingId(worksite.id); setEditingName(worksite.name); }}
                        type="button"
                      ><Pencil aria-hidden="true" className="size-4" /> Sửa</button>
                      <button
                        aria-label={`${isActive ? "Tạm ngưng" : "Kích hoạt"} ${worksite.name}`}
                        className="inline-flex min-h-10 items-center justify-center gap-1 rounded-lg border border-neutral-200 px-2 text-xs font-semibold text-neutral-700 transition hover:border-neutral-400 hover:text-neutral-950 disabled:opacity-50"
                        disabled={isUpdating}
                        onClick={() => void toggle(worksite)}
                        type="button"
                      >
                        <Power aria-hidden="true" className="size-4" /> {isActive ? "Tạm ngưng" : "Kích hoạt"}
                      </button>
                      </div>
                    </div>
                    {editingId === worksite.id ? (
                      <form className="mt-3 flex flex-col gap-2" onSubmit={(event) => { event.preventDefault(); void rename(worksite); }}>
                        <label className="text-xs font-semibold text-neutral-800" htmlFor={`worksite-name-${worksite.id}`}>Tên địa điểm</label>
                        <input className={fieldClass} id={`worksite-name-${worksite.id}`} maxLength={160} onChange={(event) => setEditingName(event.target.value)} value={editingName} />
                        <div className="flex gap-2"><button className="min-h-10 rounded-lg bg-primary-700 px-3 text-xs font-semibold text-white disabled:opacity-50" disabled={isUpdating} type="submit">Lưu tên</button><button className="min-h-10 rounded-lg px-3 text-xs text-neutral-700" onClick={() => setEditingId(null)} type="button">Hủy</button></div>
                      </form>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </section>
  );
}

function WorksiteSkeleton() {
  return (
    <div
      aria-busy="true"
      aria-label="Đang tải điểm chấm công"
      className="grid gap-3 sm:grid-cols-2"
    >
      {Array.from({ length: 2 }).map((_, index) => (
        <div
          className="h-36 animate-pulse rounded-2xl bg-neutral-100"
          key={index}
        />
      ))}
    </div>
  );
}
