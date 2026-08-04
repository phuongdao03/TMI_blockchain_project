"use client";

import { AlertTriangle, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface ConflictInput {
  hasConflict: boolean;
  reason: string | null;
}

export function ConflictGate({
  isPending,
  onDeclare,
}: {
  isPending: boolean;
  onDeclare: (input: ConflictInput) => Promise<void>;
}) {
  const [showConflict, setShowConflict] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  async function declareConflict() {
    const normalized = reason.trim();
    if (!normalized) {
      setError("Vui lòng mô tả xung đột lợi ích.");
      return;
    }
    setError("");
    await onDeclare({ hasConflict: true, reason: normalized });
  }

  return (
    <Card className="overflow-hidden border-amber-200">
      <div className="grid gap-6 p-6 sm:p-8 lg:grid-cols-[auto_minmax(0,1fr)]">
        <span className="grid size-12 place-items-center rounded-2xl bg-amber-50 text-amber-700">
          <ShieldCheck aria-hidden="true" className="size-6" />
        </span>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-amber-700">
            Bước bảo vệ tính độc lập
          </p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight">
            Xác nhận xung đột lợi ích
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
            Nội dung hồ sơ và bằng chứng chỉ hiển thị sau khi bạn xác nhận không
            có quan hệ có thể ảnh hưởng đến đánh giá.
          </p>
          {!showConflict ? (
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Button
                disabled={isPending}
                onClick={() =>
                  void onDeclare({
                    hasConflict: false,
                    reason: null,
                  }).catch(() => undefined)
                }
              >
                Tôi không có xung đột
              </Button>
              <Button
                disabled={isPending}
                onClick={() => setShowConflict(true)}
                variant="outline"
              >
                <AlertTriangle aria-hidden="true" className="size-4" />
                Tôi có xung đột lợi ích
              </Button>
            </div>
          ) : (
            <div className="mt-6 max-w-2xl">
              <label
                className="text-sm font-bold text-neutral-800"
                htmlFor="conflict-reason"
              >
                Lý do xung đột
              </label>
              <textarea
                aria-describedby={error ? "conflict-error" : undefined}
                className="mt-2 min-h-28 w-full rounded-xl border border-neutral-200 bg-white p-3 text-sm"
                id="conflict-reason"
                maxLength={2_000}
                onChange={(event) => setReason(event.target.value)}
                value={reason}
              />
              {error ? (
                <p
                  className="mt-2 text-sm font-semibold text-red-700"
                  id="conflict-error"
                  role="alert"
                >
                  {error}
                </p>
              ) : null}
              <div className="mt-4 flex gap-3">
                <Button
                  disabled={isPending}
                  onClick={() => void declareConflict().catch(() => undefined)}
                >
                  Xác nhận xung đột
                </Button>
                <Button
                  disabled={isPending}
                  onClick={() => {
                    setShowConflict(false);
                    setError("");
                  }}
                  variant="ghost"
                >
                  Quay lại
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
