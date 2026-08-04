"use client";

import { AlertTriangle, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function CouncilConflictGate({
  isPending,
  onDeclare,
}: {
  isPending: boolean;
  onDeclare: (input: {
    hasConflict: boolean;
    reason: string | null;
  }) => Promise<unknown>;
}) {
  const [showReason, setShowReason] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const declareConflict = () => {
    const normalized = reason.trim();
    if (!normalized) {
      setError("Vui lòng mô tả xung đột lợi ích.");
      return;
    }
    setError(null);
    void onDeclare({ hasConflict: true, reason: normalized });
  };

  return (
    <Card className="overflow-hidden border-amber-200 bg-amber-50/60 p-5 sm:p-6">
      <div className="flex gap-4">
        <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-white text-amber-700 shadow-sm">
          <ShieldCheck aria-hidden="true" className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-amber-800">
            Bước bắt buộc
          </p>
          <h2 className="mt-1 text-lg font-bold text-neutral-950">
            Xác nhận xung đột lợi ích
          </h2>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            Tuyên bố của bạn được khóa sau khi gửi và là một phần của biên bản
            Hội đồng.
          </p>
          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <Button
              disabled={isPending}
              onClick={() =>
                void onDeclare({ hasConflict: false, reason: null })
              }
            >
              <ShieldCheck aria-hidden="true" className="size-4" />
              Tôi không có xung đột
            </Button>
            <Button
              disabled={isPending}
              onClick={() => setShowReason(true)}
              variant="outline"
            >
              <AlertTriangle aria-hidden="true" className="size-4" />
              Tôi có xung đột lợi ích
            </Button>
          </div>
          {showReason ? (
            <div className="mt-5 rounded-xl border border-amber-200 bg-white p-4">
              <label
                className="text-sm font-bold text-neutral-800"
                htmlFor="council-conflict-reason"
              >
                Lý do xung đột
              </label>
              <textarea
                aria-describedby={error ? "council-conflict-error" : undefined}
                className="mt-2 min-h-28 w-full rounded-xl border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
                id="council-conflict-reason"
                maxLength={2_000}
                onChange={(event) => setReason(event.target.value)}
                value={reason}
              />
              {error ? (
                <p
                  className="mt-2 text-sm font-semibold text-red-700"
                  id="council-conflict-error"
                  role="alert"
                >
                  {error}
                </p>
              ) : null}
              <div className="mt-3 flex justify-end">
                <Button
                  disabled={isPending}
                  onClick={declareConflict}
                  variant="outline"
                >
                  Xác nhận xung đột
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  );
}
