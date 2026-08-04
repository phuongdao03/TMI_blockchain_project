import { BadgeCheck, CircleMinus, ShieldAlert } from "lucide-react";

import type {
  CouncilCaseResult,
  CouncilVoteChoice,
} from "@/lib/api/types";

const decisionLabels = {
  APPROVE: "Phê duyệt hồ sơ",
  REJECT: "Từ chối hồ sơ",
  REQUEST_MORE_INFO: "Yêu cầu bổ sung",
} as const;

const voteLabels: Record<CouncilVoteChoice, string> = {
  APPROVE: "Phê duyệt",
  REJECT: "Từ chối",
  REQUEST_MORE_INFO: "Yêu cầu bổ sung",
  ABSTAIN: "Không biểu quyết",
};

export function CouncilResultPanel({
  result,
}: {
  result: CouncilCaseResult;
}) {
  return (
    <section
      aria-labelledby={`result-${result.caseId}`}
      className="rounded-2xl border border-neutral-200 bg-white p-5"
    >
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary-700">
          {result.decision ? (
            <BadgeCheck aria-hidden="true" className="size-5" />
          ) : result.quorumMet ? (
            <CircleMinus aria-hidden="true" className="size-5" />
          ) : (
            <ShieldAlert aria-hidden="true" className="size-5" />
          )}
        </span>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-neutral-500">
            Kết quả chính thức
          </p>
          <h3
            className="mt-1 text-lg font-bold text-neutral-950"
            id={`result-${result.caseId}`}
          >
            {result.decision
              ? decisionLabels[result.decision]
              : result.quorumMet
                ? "Không đạt đa số tuyệt đối"
                : "Không đủ quorum"}
          </h3>
          <p className="mt-1 text-sm text-neutral-500">
            {result.validVoteCount} phiếu hợp lệ ·{" "}
            {result.quorumMet ? "Đủ quorum" : "Chưa đủ quorum"}
          </p>
        </div>
      </div>
      <dl className="mt-5 grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-neutral-200 sm:grid-cols-4">
        {(Object.entries(voteLabels) as Array<[CouncilVoteChoice, string]>).map(
          ([choice, label]) => (
            <div className="bg-neutral-50 p-3" key={choice}>
              <dt className="text-xs font-semibold text-neutral-500">
                {label}
              </dt>
              <dd className="mt-1 text-xl font-bold text-neutral-950">
                {result.voteCounts[choice]}
              </dd>
            </div>
          ),
        )}
      </dl>
    </section>
  );
}
