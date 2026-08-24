"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Hash, LoaderCircle } from "lucide-react";
import Link from "next/link";

import { CouncilCasePanel } from "@/components/council/council-case-panel";
import { CouncilSessionHero } from "@/components/council/council-session-hero";
import { councilApi } from "@/lib/api/client";
import type { CouncilVoteChoice } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";
import { councilKeys } from "@/lib/council/query-keys";

export function CouncilWorkspace({ sessionId }: { sessionId: string }) {
  const user = useAuthUser();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: councilKeys.detail(sessionId),
    queryFn: () => councilApi.get(sessionId),
  });
  const minutes = useQuery({
    queryKey: [...councilKeys.detail(sessionId), "minutes"],
    queryFn: () => councilApi.minutes(sessionId),
    enabled: query.data?.session.status === "CLOSED",
  });
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: councilKeys.detail(sessionId),
      }),
      queryClient.invalidateQueries({ queryKey: councilKeys.lists() }),
    ]);
  };
  const attendance = useMutation({
    mutationFn: () => councilApi.confirmAttendance(sessionId),
    onSuccess: refresh,
  });
  const lifecycle = useMutation({
    mutationFn: (action: "open" | "close") =>
      action === "open"
        ? councilApi.open(sessionId)
        : councilApi.close(sessionId),
    onSuccess: refresh,
  });
  const conflict = useMutation({
    mutationFn: ({
      caseId,
      input,
    }: {
      caseId: string;
      input: { hasConflict: boolean; reason: string | null };
    }) => councilApi.declareConflict(caseId, input),
    onSuccess: refresh,
  });
  const vote = useMutation({
    mutationFn: ({
      caseId,
      input,
    }: {
      caseId: string;
      input: { choice: CouncilVoteChoice; reason: string };
    }) => councilApi.vote(caseId, input),
    onSuccess: refresh,
  });

  if (query.isPending) {
    return (
      <div className="grid min-h-[60vh] place-items-center" role="status">
        <span className="flex items-center gap-3 font-semibold text-neutral-600">
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          Đang mở phiên Hội đồng…
        </span>
      </div>
    );
  }
  if (query.error || !query.data) {
    return (
      <div
        className="rounded-2xl border border-red-200 bg-red-50 p-6 font-semibold text-red-800"
        role="alert"
      >
        Không thể mở phiên Hội đồng hoặc bạn không còn quyền truy cập.
      </div>
    );
  }

  const detail = query.data;
  const isMember = user?.roles.includes("SUPER_ADMIN") === true;
  const canManage = isMember;
  const canVote =
    isMember &&
    detail.session.status === "OPEN" &&
    Boolean(detail.myAttendanceConfirmedAt);
  const mutationError =
    attendance.error ?? lifecycle.error ?? conflict.error ?? vote.error;

  return (
    <div className="mx-auto max-w-[92rem] space-y-6">
      <Link
        className="inline-flex min-h-11 items-center gap-2 text-sm font-bold text-neutral-600 hover:text-primary-700"
        href="/council"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        Trở lại lịch Hội đồng
      </Link>
      <CouncilSessionHero
        canManage={canManage}
        isMember={isMember}
        isPending={attendance.isPending || lifecycle.isPending}
        myAttendanceConfirmedAt={detail.myAttendanceConfirmedAt}
        onAttendance={() => attendance.mutate()}
        onLifecycle={(action) => lifecycle.mutate(action)}
        session={detail.session}
      />
      {mutationError ? (
        <p
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800"
          role="alert"
        >
          Thao tác không thành công. Vui lòng kiểm tra trạng thái phiên và thử
          lại.
        </p>
      ) : null}
      <div className="grid gap-5">
        {detail.cases.map((item) => (
          <CouncilCasePanel
            canVote={canVote}
            detail={item}
            isConflictPending={conflict.isPending}
            isVotePending={vote.isPending}
            key={item.case.id}
            onConflict={(input) =>
              conflict.mutateAsync({ caseId: item.case.id, input })
            }
            onVote={(input) =>
              vote.mutateAsync({ caseId: item.case.id, input })
            }
          />
        ))}
      </div>
      {minutes.data ? (
        <footer className="rounded-2xl border bg-white p-5 sm:p-6">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-neutral-500">
            <Hash aria-hidden="true" className="size-4" />
            Dấu vân tay biên bản
          </p>
          <code className="mt-3 block break-all rounded-xl bg-neutral-950 p-4 text-xs text-emerald-300">
            {minutes.data.minutesHash}
          </code>
        </footer>
      ) : null}
    </div>
  );
}
