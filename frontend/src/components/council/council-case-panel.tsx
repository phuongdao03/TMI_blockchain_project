import { CheckCircle2, FileText, LockKeyhole, ShieldAlert } from "lucide-react";

import { CouncilConflictGate } from "@/components/council/council-conflict-gate";
import { CouncilResultPanel } from "@/components/council/council-result-panel";
import { CouncilVoteDialog } from "@/components/council/council-vote-dialog";
import { Card } from "@/components/ui/card";
import type { CouncilCaseDetail, CouncilVoteChoice } from "@/lib/api/types";

export function CouncilCasePanel({
  canVote,
  detail,
  isConflictPending,
  isVotePending,
  onConflict,
  onVote,
}: {
  canVote: boolean;
  detail: CouncilCaseDetail;
  isConflictPending: boolean;
  isVotePending: boolean;
  onConflict: (input: {
    hasConflict: boolean;
    reason: string | null;
  }) => Promise<unknown>;
  onVote: (input: {
    choice: CouncilVoteChoice;
    reason: string;
  }) => Promise<unknown>;
}) {
  return (
    <article className="space-y-4">
      <Card className="overflow-hidden">
        <div className="border-b bg-neutral-50/80 p-5 sm:p-6">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
            <div>
              <p className="font-mono text-xs font-bold text-primary-700">
                {detail.case.dossierCode} · V{detail.case.versionNo}
              </p>
              <h2 className="mt-2 text-xl font-bold tracking-tight">
                {detail.case.dossierTitle}
              </h2>
            </div>
            <span className="inline-flex w-fit items-center gap-2 rounded-full border bg-white px-3 py-1.5 text-xs font-bold text-neutral-600">
              <FileText aria-hidden="true" className="size-4" />
              Hồ sơ trong phiên
            </span>
          </div>
        </div>
        <div className="p-5 sm:p-6">
          {detail.myVote ? (
            <div className="flex gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-900">
              <CheckCircle2 aria-hidden="true" className="mt-0.5 size-5" />
              <div>
                <p className="font-bold">Kết quả của bạn đã được ghi nhận</p>
                <p className="mt-1 text-sm">
                  Kết quả đã được lưu vào biên bản phiên và không thể chỉnh sửa.
                </p>
              </div>
            </div>
          ) : detail.myConflict?.hasConflict ? (
            <div className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
              <ShieldAlert aria-hidden="true" className="mt-0.5 size-5" />
              <div>
                <p className="font-bold">Hồ sơ không được phân công cho bạn</p>
                <p className="mt-1 text-sm">
                  Bạn không thể gửi kết quả xử lý cho hồ sơ này.
                </p>
              </div>
            </div>
          ) : canVote && detail.myConflict ? (
            <CouncilVoteDialog isPending={isVotePending} onVote={onVote} />
          ) : canVote ? (
            <CouncilConflictGate
              isPending={isConflictPending}
              onDeclare={onConflict}
            />
          ) : (
            <div className="flex gap-3 rounded-xl border bg-neutral-50 p-4 text-neutral-600">
              <LockKeyhole aria-hidden="true" className="mt-0.5 size-5" />
              <p className="text-sm font-semibold">
                Chưa thể gửi kết quả ở trạng thái hiện tại.
              </p>
            </div>
          )}
        </div>
      </Card>
      {detail.result ? <CouncilResultPanel result={detail.result} /> : null}
    </article>
  );
}
