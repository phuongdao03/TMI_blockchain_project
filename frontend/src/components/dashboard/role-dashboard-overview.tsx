import {
  ArrowRight,
  ClipboardCheck,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

import { ApplicantUpgradeCard } from "@/components/dashboard/applicant-upgrade-card";
import type { AccountType, AuthUser } from "@/lib/api/types";
import type { WorkspacePersona } from "@/lib/auth/role-workspaces";

type RoleWorkspacePersona = WorkspacePersona;

interface Action {
  href: string;
  label: string;
  detail: string;
  icon: typeof Search;
}

const publicAction: Action = {
  href: "/search",
  label: "Tìm kiếm đề cử",
  detail: "Tìm theo tên, chủ đề hoặc danh mục.",
  icon: Search,
};

const staffWorkspaces: Record<
  Exclude<RoleWorkspacePersona, "VIEWER" | "USER">,
  {
    eyebrow: string;
    title: string;
    description: string;
    primaryAction: Action;
  }
> = {
  MODERATOR: {
    eyebrow: "Khu vực thẩm định",
    title: "Hàng đợi thẩm định",
    description:
      "Tập trung vào hồ sơ được phân công, tiêu chí 5T và các mốc SLA cần xử lý.",
    primaryAction: {
      href: "/reviews",
      label: "Mở hàng đợi thẩm định",
      detail: "Xem phân công và tiếp tục phiên đánh giá.",
      icon: ClipboardCheck,
    },
  },
  SUPER_ADMIN: {
    eyebrow: "Khu vực điều hành",
    title: "Điều hành toàn hệ thống",
    description:
      "Quan sát vận hành liên phòng ban, kiểm soát ngoại lệ và truy cập các công cụ quản trị được cấp.",
    primaryAction: {
      href: "/admin/dashboard",
      label: "Mở bảng điều hành",
      detail: "Tổng quan vận hành và tín hiệu cần ưu tiên.",
      icon: ShieldCheck,
    },
  },
};

export function RoleDashboardOverview({
  persona,
  accountType,
  onUpgraded,
}: {
  persona: RoleWorkspacePersona;
  accountType?: AccountType | null;
  onUpgraded?: (user: AuthUser) => void;
}) {
  const isViewer = persona === "VIEWER";
  const workspace =
    persona === "VIEWER" || persona === "USER"
      ? undefined
      : staffWorkspaces[persona];
  const title = workspace?.title ?? "Tra cứu đề cử và chứng thư";
  const description = isViewer
    ? "Tài khoản tra cứu đã sẵn sàng. Tìm nội dung công khai hoặc kiểm tra trạng thái chứng thư bằng mã được cung cấp."
    : (workspace?.description ?? "");
  const primaryAction = workspace?.primaryAction ?? publicAction;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <header>
        <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-primary-700">
          {isViewer ? "Không gian tra cứu" : "Công việc hôm nay"}
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-[-0.04em] sm:text-4xl">
          {title}
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-neutral-600">
          {description}
        </p>
      </header>

      {isViewer && accountType === "PUBLIC_USER" ? (
        <ApplicantUpgradeCard onUpgraded={onUpgraded} />
      ) : null}

      {isViewer ? (
        <nav
          aria-label="Việc có thể làm với tài khoản tra cứu"
          className="flex flex-wrap gap-3"
        >
          <Link
            className="inline-flex min-h-11 items-center rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm font-bold text-[var(--theme-text)]"
            href="/verify"
          >
            Tra cứu chứng thư
          </Link>
          <Link
            className="inline-flex min-h-11 items-center rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm font-bold text-[var(--theme-text)]"
            href="/help"
          >
            Xem hướng dẫn tài khoản
          </Link>
        </nav>
      ) : null}

      {primaryAction ? (
        <section className="hero-grid-surface relative overflow-hidden rounded-2xl bg-neutral-950 px-6 py-8 text-white shadow-[0_24px_70px_rgb(15_15_15/0.16)] sm:px-8 lg:grid lg:min-h-72 lg:grid-cols-[1fr_auto] lg:items-end lg:px-10 lg:py-10">
          <div className="relative z-10 max-w-2xl">
            <span className="grid size-11 place-items-center rounded-lg border border-gold-300/30 bg-gold-300/10 text-gold-300">
              {isViewer ? (
                <Sparkles aria-hidden="true" className="size-5" />
              ) : (
                <ShieldCheck aria-hidden="true" className="size-5" />
              )}
            </span>
            <p className="mt-7 font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-gold-300">
              Bắt đầu tại đây
            </p>
            <h2 className="mt-3 text-2xl font-bold tracking-[-0.03em] sm:text-3xl">
              {primaryAction.label}
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              {primaryAction.detail}
            </p>
          </div>
          <Link
            className="relative z-10 mt-8 inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-primary-600 px-5 text-sm font-bold text-white hover:bg-primary-500 lg:mt-0"
            href={primaryAction.href}
          >
            {primaryAction.label}
            <ArrowRight aria-hidden="true" className="size-4" />
          </Link>
        </section>
      ) : null}
    </div>
  );
}
