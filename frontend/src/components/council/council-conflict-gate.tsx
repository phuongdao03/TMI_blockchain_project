"use client";

import { ClipboardCheck } from "lucide-react";

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
  return (
    <Card className="overflow-hidden border-amber-200 bg-amber-50/60 p-5 sm:p-6">
      <div className="flex gap-4">
        <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-white text-amber-700 shadow-sm">
          <ClipboardCheck aria-hidden="true" className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-amber-800">
            Bắt đầu xử lý
          </p>
          <h2 className="mt-1 text-lg font-bold text-neutral-950">
            Tiếp nhận hồ sơ trong phiên này
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
            Xác nhận để xem nội dung cần quyết định và gửi kết quả xử lý. Mỗi
            nhân sự chỉ gửi một kết quả cho hồ sơ trong phiên.
          </p>
          <Button
            className="mt-5"
            disabled={isPending}
            onClick={() => void onDeclare({ hasConflict: false, reason: null })}
          >
            <ClipboardCheck aria-hidden="true" className="size-4" />
            {isPending ? "Đang tiếp nhận…" : "Tiếp nhận hồ sơ"}
          </Button>
        </div>
      </div>
    </Card>
  );
}
