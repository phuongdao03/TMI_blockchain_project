"use client";

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ConfirmationDialog({
  confirmLabel,
  description,
  isPending,
  onCancel,
  onConfirm,
  open,
  title,
}: {
  confirmLabel: string;
  description: string;
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  open: boolean;
  title: string;
}) {
  if (!open) return null;

  return (
    <div
      aria-labelledby="confirmation-title"
      aria-modal="true"
      className="fixed inset-0 z-50 grid place-items-center bg-ink-950/70 p-4 backdrop-blur-sm"
      role="dialog"
    >
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-white p-6 shadow-2xl">
        <span className="grid size-11 place-items-center rounded-xl bg-amber-50 text-amber-700">
          <AlertTriangle aria-hidden="true" className="size-5" />
        </span>
        <h2
          className="mt-4 text-xl font-bold tracking-tight text-neutral-950"
          id="confirmation-title"
        >
          {title}
        </h2>
        <p className="mt-2 text-sm leading-6 text-neutral-600">{description}</p>
        <div className="mt-6 flex justify-end gap-3">
          <Button disabled={isPending} onClick={onCancel} variant="ghost">
            Quay lại
          </Button>
          <Button disabled={isPending} onClick={onConfirm}>
            {isPending ? "Đang gửi…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
