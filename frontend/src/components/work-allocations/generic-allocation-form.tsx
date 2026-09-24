"use client";

import { useMutation } from "@tanstack/react-query";
import { Plus, UsersRound } from "lucide-react";
import { type FormEvent, useState } from "react";

import { ApiError, workAllocationAdminApi } from "@/lib/api/client";
import type { StaffAccount, WorkAllocationPriority } from "@/lib/api/types";

const fieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100 dark:border-neutral-700 dark:bg-neutral-950 dark:text-neutral-50 dark:focus:border-primary-400 dark:focus:ring-primary-950";

const priorityLabels: Record<WorkAllocationPriority, string> = {
  LOW: "Thấp",
  MEDIUM: "Trung bình",
  HIGH: "Cao",
  CRITICAL: "Khẩn cấp",
};

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Chưa thể lưu phân công. Vui lòng kiểm tra thông tin và thử lại.";
}

export function GenericAllocationForm({
  staff,
  onSaved,
}: {
  staff: StaffAccount[];
  onSaved: () => Promise<void>;
}) {
  const [objective, setObjective] = useState("");
  const [description, setDescription] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [priority, setPriority] = useState<WorkAllocationPriority>("MEDIUM");
  const [selectedMemberIds, setSelectedMemberIds] = useState<string[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () =>
      workAllocationAdminApi.create({
        kind: "GENERIC",
        objective: objective.trim(),
        description: description.trim() || null,
        dueAt: dueAt ? new Date(dueAt).toISOString() : null,
        priority,
        members: selectedMemberIds.map((userId) => ({
          userId,
          responsibility: "CONTRIBUTOR",
        })),
      }),
    onSuccess: async () => {
      setObjective("");
      setDescription("");
      setDueAt("");
      setPriority("MEDIUM");
      setSelectedMemberIds([]);
      setFormError(null);
      await onSaved();
    },
  });

  function toggleMember(userId: string) {
    setSelectedMemberIds((selected) =>
      selected.includes(userId)
        ? selected.filter((id) => id !== userId)
        : [...selected, userId],
    );
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!objective.trim()) {
      setFormError("Mục tiêu công việc là bắt buộc.");
      return;
    }
    setFormError(null);
    create.mutate();
  }

  return (
    <form
      aria-label="Tạo công việc chung"
      className="rounded-2xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900 sm:p-6"
      onSubmit={submit}
    >
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-100 text-primary-800 dark:bg-primary-950 dark:text-primary-200">
          <Plus aria-hidden="true" className="size-5" />
        </span>
        <div>
          <h2 className="text-xl font-bold text-neutral-950 dark:text-white">
            Công việc chung
          </h2>
          <p className="mt-1 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
            Tạo đầu việc rõ ràng và ghi nhận người cùng chịu trách nhiệm.
          </p>
        </div>
      </div>

      <label className="mt-6 block text-sm font-bold text-neutral-800 dark:text-neutral-100">
        Mục tiêu công việc
        <input
          className={fieldClass}
          maxLength={240}
          onChange={(event) => setObjective(event.target.value)}
          value={objective}
        />
      </label>
      <label className="mt-4 block text-sm font-bold text-neutral-800 dark:text-neutral-100">
        Mô tả{" "}
        <span className="font-normal text-neutral-500">(không bắt buộc)</span>
        <textarea
          className={`${fieldClass} min-h-24 py-3`}
          maxLength={10000}
          onChange={(event) => setDescription(event.target.value)}
          value={description}
        />
      </label>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-bold text-neutral-800 dark:text-neutral-100">
          Hạn hoàn thành
          <input
            className={fieldClass}
            onChange={(event) => setDueAt(event.target.value)}
            type="datetime-local"
            value={dueAt}
          />
        </label>
        <label className="text-sm font-bold text-neutral-800 dark:text-neutral-100">
          Mức độ ưu tiên
          <select
            className={fieldClass}
            onChange={(event) =>
              setPriority(event.target.value as WorkAllocationPriority)
            }
            value={priority}
          >
            {Object.entries(priorityLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <fieldset className="mt-6">
        <legend className="flex items-center gap-2 text-sm font-bold text-neutral-800 dark:text-neutral-100">
          <UsersRound aria-hidden="true" className="size-4 text-primary-700" />
          Người cùng thực hiện
        </legend>
        {staff.length === 0 ? (
          <p className="mt-3 rounded-xl bg-neutral-50 p-4 text-sm leading-6 text-neutral-600 dark:bg-neutral-950 dark:text-neutral-300">
            Chưa có Moderator đang hoạt động để thêm vào công việc.
          </p>
        ) : (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {staff.map((person) => (
              <label
                className="flex min-h-11 items-center gap-3 rounded-xl border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-800 transition has-[:checked]:border-primary-500 has-[:checked]:bg-primary-50 dark:border-neutral-700 dark:text-neutral-100 dark:has-[:checked]:bg-primary-950"
                key={person.id}
              >
                <input
                  aria-label={person.email}
                  checked={selectedMemberIds.includes(person.id)}
                  className="size-4 accent-primary-700"
                  onChange={() => toggleMember(person.id)}
                  type="checkbox"
                />
                <span className="min-w-0 truncate">{person.email}</span>
              </label>
            ))}
          </div>
        )}
      </fieldset>

      {formError || create.error ? (
        <p
          className="mt-5 text-sm font-semibold text-red-700 dark:text-red-300"
          role="alert"
        >
          {formError ?? errorMessage(create.error)}
        </p>
      ) : null}
      <button
        className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary-700 px-5 text-sm font-bold text-white transition hover:bg-primary-800 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60 dark:bg-primary-400 dark:text-neutral-950 dark:hover:bg-primary-300"
        disabled={create.isPending}
        type="submit"
      >
        <Plus aria-hidden="true" className="size-4" />
        {create.isPending ? "Đang lưu..." : "Lưu phân công"}
      </button>
    </form>
  );
}
