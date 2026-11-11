"use client";

import { LoaderCircle, RotateCcw } from "lucide-react";
import type { ReactNode } from "react";

export const PAGE_SIZE = 20;

export function ActionButton({
  children,
  onClick,
  disabled,
  danger = false,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      className={danger ? dangerButtonClass : secondaryButtonClass}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

export function Pagination({
  page,
  totalPages,
  label,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  label: string;
  onPageChange: (page: number) => void;
}) {
  return (
    <nav
      aria-label={label}
      className="mt-5 flex items-center justify-between gap-3 border-t border-[var(--theme-border)] py-4"
    >
      <button
        className={secondaryButtonClass}
        disabled={page <= 1}
        onClick={() => onPageChange(Math.max(1, page - 1))}
        type="button"
      >
        Trang trước
      </button>
      <p aria-live="polite" className="text-sm text-[var(--theme-muted)]">
        Trang {page} / {totalPages}
      </p>
      <button
        className={secondaryButtonClass}
        disabled={page >= totalPages}
        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        type="button"
      >
        Trang sau
      </button>
    </nav>
  );
}

export function LoadingState({ label }: { label: string }) {
  return (
    <p
      aria-busy="true"
      className="mt-5 flex items-center gap-2 text-sm text-[var(--theme-muted)]"
      role="status"
    >
      <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
      {label}.
    </p>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      className="mt-5 rounded-xl border border-red-300 bg-red-50 p-4"
      role="alert"
    >
      <p className="text-sm font-semibold text-red-900">{message}</p>
      <button
        className={`${secondaryButtonClass} mt-3`}
        onClick={onRetry}
        type="button"
      >
        <RotateCcw aria-hidden="true" className="size-4" />
        Thử tải lại
      </button>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <p
      className="mt-5 rounded-xl border border-dashed border-[var(--theme-border)] p-8 text-center text-sm text-[var(--theme-muted)]"
      role="status"
    >
      {message}
    </p>
  );
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa rõ";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export const inputClass =
  "mt-1 min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 py-2 text-sm font-normal text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20";
export const textareaClass =
  "mt-1 w-full resize-y rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 text-sm font-normal leading-6 text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20";
export const cardClass =
  "rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5";
export const statusBadgeClass =
  "inline-flex rounded-full bg-[var(--theme-accent)]/10 px-2.5 py-1 text-xs font-bold text-[var(--theme-accent)]";
export const softBadgeClass =
  "inline-flex rounded-full bg-[var(--theme-elevated)] px-2.5 py-1 text-xs font-semibold text-[var(--theme-muted)]";
export const primaryButtonClass =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50";
export const secondaryButtonClass =
  "inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--theme-border)] px-3 text-sm font-semibold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50";
export const dangerButtonClass =
  "inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-red-300 px-3 text-sm font-semibold text-red-700 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700 disabled:cursor-not-allowed disabled:opacity-50";
