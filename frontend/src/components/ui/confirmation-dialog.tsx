"use client";

import { AlertTriangle } from "lucide-react";
import {
  type KeyboardEvent,
  type ReactNode,
  useEffect,
  useId,
  useRef,
} from "react";

import { Button } from "@/components/ui/button";

export function ConfirmationDialog({
  confirmLabel,
  confirmDisabled = false,
  description,
  isPending,
  onCancel,
  onConfirm,
  open,
  title,
  children,
}: {
  confirmLabel: string;
  confirmDisabled?: boolean;
  description: string;
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  open: boolean;
  title: string;
  children?: ReactNode;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const confirm =
      dialogRef.current?.querySelector<HTMLElement>(
        "[data-dialog-initial-focus]",
      ) ??
      dialogRef.current?.querySelector<HTMLElement>(
        "[data-dialog-confirm]:not(:disabled)",
      ) ??
      dialogRef.current?.querySelector<HTMLElement>("button:not(:disabled)");
    confirm?.focus();
    return () => previouslyFocused?.focus();
  }, [open]);

  if (!open) return null;

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
      return;
    }
    if (event.key !== "Tab") return;

    const controls = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(
        "button:not(:disabled), textarea:not(:disabled), input:not(:disabled), select:not(:disabled)",
      ) ?? [],
    );
    if (controls.length === 0) return;
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  }

  return (
    <div
      aria-labelledby={titleId}
      aria-modal="true"
      className="fixed inset-0 z-50 grid place-items-center bg-ink-950/70 p-4 backdrop-blur-sm"
      onKeyDown={handleKeyDown}
      ref={dialogRef}
      role="dialog"
    >
      <div className="confirmation-dialog__surface w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
        <span className="grid size-11 place-items-center rounded-xl bg-amber-50 text-amber-700">
          <AlertTriangle aria-hidden="true" className="size-5" />
        </span>
        <h2
          className="mt-4 text-xl font-bold tracking-tight text-neutral-950"
          id={titleId}
        >
          {title}
        </h2>
        <p className="mt-2 text-sm leading-6 text-neutral-600">{description}</p>
        {children}
        <div className="mt-6 flex justify-end gap-3">
          <Button disabled={isPending} onClick={onCancel} variant="ghost">
            Quay lại
          </Button>
          <Button
            data-dialog-confirm
            disabled={isPending || confirmDisabled}
            onClick={onConfirm}
          >
            {isPending ? "Đang gửi…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
