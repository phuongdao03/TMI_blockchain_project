import {
  CalendarDays,
  CheckCircle2,
  Landmark,
  LockKeyhole,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import type { CouncilSession } from "@/lib/api/types";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

export function CouncilSessionHero({
  canManage,
  isMember,
  isPending,
  myAttendanceConfirmedAt,
  onAttendance,
  onLifecycle,
  session,
}: {
  canManage: boolean;
  isMember: boolean;
  isPending: boolean;
  myAttendanceConfirmedAt: string | null;
  onAttendance: () => void;
  onLifecycle: (action: "open" | "close") => void;
  session: CouncilSession;
}) {
  return (
    <header className="relative overflow-hidden rounded-3xl bg-ink-950 p-6 text-white shadow-2xl shadow-slate-950/15 sm:p-8">
      <div
        aria-hidden="true"
        className="absolute right-0 -top-20 size-72 rounded-full border border-white/10 bg-primary-600/15"
      />
      <div className="relative flex flex-col justify-between gap-7 xl:flex-row xl:items-end">
        <div>
          <p className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-200">
            <Landmark aria-hidden="true" className="size-4" />
            {session.code}
          </p>
          <h1 className="mt-3 max-w-4xl text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
            {session.title}
          </h1>
          <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-300">
            <span className="flex items-center gap-2">
              <CalendarDays aria-hidden="true" className="size-4" />
              {formatDate(session.scheduledAt)}
            </span>
            <span className="flex items-center gap-2">
              <Users aria-hidden="true" className="size-4" />
              {session.attendanceCount}/{session.memberCount} người đã tham gia
              · cần tối thiểu {session.quorumRequired}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          {isMember &&
          session.status === "DRAFT" &&
          !myAttendanceConfirmedAt ? (
            <Button disabled={isPending} onClick={onAttendance}>
              <CheckCircle2 aria-hidden="true" className="size-4" />
              Xác nhận tham dự
            </Button>
          ) : null}
          {canManage && session.status === "DRAFT" ? (
            <Button
              disabled={isPending}
              onClick={() => onLifecycle("open")}
              variant="outline"
            >
              Bắt đầu xét duyệt
            </Button>
          ) : null}
          {canManage && session.status === "OPEN" ? (
            <Button
              disabled={isPending}
              onClick={() => onLifecycle("close")}
              variant="outline"
            >
              <LockKeyhole aria-hidden="true" className="size-4" />
              Kết thúc phiên
            </Button>
          ) : null}
        </div>
      </div>
    </header>
  );
}
