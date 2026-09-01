import {
  ArrowRight,
  BadgeCheck,
  BookOpenText,
  ClipboardCheck,
  Map,
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

const publicActions: Action[] = [
  {
    href: "/search",
    label: "Tìm kiếm đề cử",
    detail: "Tìm theo tên, chủ đề hoặc danh mục.",
    icon: Search,
  },
  {
    href: "/works",
    label: "Thư viện đề cử",
    detail: "Khám phá những nội dung đã được công bố.",
    icon: BookOpenText,
  },
  {
    href: "/map",
    label: "Bản đồ đề cử",
    detail: "Khám phá nội dung theo địa điểm và khu vực.",
    icon: Map,
  },
  {
    href: "/verify",
    label: "Tra cứu chứng thư",
    detail: "Kiểm tra trạng thái và thông tin đã công bố.",
    icon: BadgeCheck,
  },
];

const staffWorkspaces: Record<
  Exclude<RoleWorkspacePersona, "VIEWER" | "USER">,
  {
    eyebrow: string;
    title: string;
    description: string;
    actions: Action[];
  }
> = {
  MODERATOR: {
    eyebrow: "Khu vực thẩm định",
    title: "Hàng đợi thẩm định",
    description:
      "Tập trung vào hồ sơ được phân công, tiêu chí 5T và các mốc SLA cần xử lý.",
    actions: [
      {
        href: "/reviews",
        label: "Mở hàng đợi thẩm định",
        detail: "Xem phân công và tiếp tục phiên đánh giá.",
        icon: ClipboardCheck,
      },
      {
        href: "/council",
        label: "Phiên xét duyệt",
        detail: "Khai báo xung đột, biểu quyết và theo dõi biên bản.",
        icon: BadgeCheck,
      },
    ],
  },
  SUPER_ADMIN: {
    eyebrow: "Khu vực điều hành",
    title: "Điều hành toàn hệ thống",
    description:
      "Quan sát vận hành liên phòng ban, kiểm soát ngoại lệ và truy cập các công cụ quản trị được cấp.",
    actions: [
      {
        href: "/admin/dashboard",
        label: "Mở bảng điều hành",
        detail: "Tổng quan vận hành và tín hiệu cần ưu tiên.",
        icon: ShieldCheck,
      },
      {
        href: "/blockchain",
        label: "Ký blockchain",
        detail: "Liên kết ví và ký các bằng chứng đã được duyệt.",
        icon: ShieldCheck,
      },
    ],
  },
};

function ActionGrid({ actions }: { actions: Action[] }) {
  return (
    <section
      className="workspace-action-grid grid overflow-hidden rounded-xl border border-black/10 sm:grid-cols-2"
      aria-label="Tác vụ sẵn có"
    >
      {actions.map(({ href, label, detail, icon: Icon }) => (
        <Link
          className="workspace-action-card group min-h-40 border-b border-black/8 p-6 transition-colors sm:border-r sm:[&:nth-child(even)]:border-r-0 sm:[&:nth-last-child(-n+2)]:border-b-0"
          href={href}
          key={href}
        >
          <span className="grid size-10 place-items-center rounded-lg border border-primary-100 bg-primary-50 text-primary-700">
            <Icon aria-hidden="true" className="size-5" />
          </span>
          <span className="mt-5 flex items-center justify-between gap-3 text-base font-bold text-neutral-950">
            {label}
            <ArrowRight
              aria-hidden="true"
              className="size-4 text-neutral-400 transition group-hover:translate-x-1 group-hover:text-primary-700"
            />
          </span>
          <span className="mt-2 block text-sm leading-6 text-neutral-500">
            {detail}
          </span>
        </Link>
      ))}
    </section>
  );
}

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
  const title = workspace?.title ?? "Khám phá đề cử";
  const description = isViewer
    ? "Khám phá nội dung đã công bố và theo dõi những hoạt động mới của chương trình."
    : (workspace?.description ?? "");
  const actions = workspace?.actions ?? publicActions;
  const [primaryAction, ...secondaryActions] = actions;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <header>
        <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-primary-700">
          {isViewer ? "Không gian tra cứu" : "Công việc hôm nay"}
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">
          {title}
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-neutral-600">
          {description}
        </p>
      </header>

      {isViewer && accountType === "PUBLIC_USER" ? (
        <ApplicantUpgradeCard onUpgraded={onUpgraded} />
      ) : null}

      {primaryAction ? (
        <section className="hero-grid-surface relative overflow-hidden rounded-2xl bg-[#151515] px-6 py-8 text-white shadow-[0_24px_70px_rgb(15_15_15/0.16)] sm:px-8 lg:grid lg:min-h-72 lg:grid-cols-[1fr_auto] lg:items-end lg:px-10 lg:py-10">
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

      {secondaryActions.length ? (
        <ActionGrid actions={secondaryActions} />
      ) : null}
    </div>
  );
}
