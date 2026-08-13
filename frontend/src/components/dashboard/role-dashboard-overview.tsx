import {
  ArrowRight,
  BadgeCheck,
  BookOpenText,
  ClipboardCheck,
  Landmark,
  Map,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

import { ApplicantUpgradeCard } from "@/components/dashboard/applicant-upgrade-card";
import type { AccountType, AuthUser } from "@/lib/api/types";
import type { WorkspacePersona } from "@/lib/auth/role-workspaces";

type RoleWorkspacePersona = Exclude<WorkspacePersona, "APPLICANT">;

interface Action {
  href: string;
  label: string;
  detail: string;
  icon: typeof Search;
}

const publicActions: Action[] = [
  {
    href: "/search",
    label: "Tìm tài sản số",
    detail: "Tra cứu theo mã, tên hoặc tổ chức phát hành.",
    icon: Search,
  },
  {
    href: "/works",
    label: "Thư viện chứng thư",
    detail: "Khám phá các tài sản đã được công khai.",
    icon: BookOpenText,
  },
  {
    href: "/map",
    label: "Bản đồ xác lập",
    detail: "Xem hệ sinh thái tài sản theo khu vực.",
    icon: Map,
  },
  {
    href: "/verify",
    label: "Xác minh chứng thư",
    detail: "Đối chiếu tính toàn vẹn của chứng thư công khai.",
    icon: BadgeCheck,
  },
];

const staffWorkspaces: Record<
  Exclude<RoleWorkspacePersona, "PUBLIC">,
  {
    eyebrow: string;
    title: string;
    description: string;
    actions: Action[];
  }
> = {
  REVIEWER: {
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
        href: "/notifications",
        label: "Thông báo công việc",
        detail: "Theo dõi thay đổi phân công và nhắc hạn.",
        icon: BadgeCheck,
      },
    ],
  },
  COUNCIL: {
    eyebrow: "Khu vực Hội đồng",
    title: "Phiên xét duyệt Hội đồng",
    description:
      "Rà soát chương trình họp, công khai xung đột lợi ích và biểu quyết theo phiên.",
    actions: [
      {
        href: "/council",
        label: "Mở phiên Hội đồng",
        detail: "Xem agenda, biên bản và quyết định đang chờ.",
        icon: Landmark,
      },
      {
        href: "/notifications",
        label: "Thông báo phiên họp",
        detail: "Theo dõi lịch và thay đổi của Hội đồng.",
        icon: BadgeCheck,
      },
    ],
  },
  ADMIN: {
    eyebrow: "Khu vực vận hành",
    title: "Điều hành nền tảng",
    description:
      "Theo dõi nội dung, vận hành và các ngoại lệ thuộc đúng phạm vi quản trị của bạn.",
    actions: [
      {
        href: "/admin/dashboard",
        label: "Mở bảng vận hành",
        detail: "Theo dõi chỉ số vận hành và các ngoại lệ cần xử lý.",
        icon: ShieldCheck,
      },
      {
        href: "/notifications",
        label: "Thông báo vận hành",
        detail: "Theo dõi các sự kiện và ngoại lệ thuộc phạm vi của bạn.",
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
        href: "/admin/audit",
        label: "Nhật ký kiểm toán",
        detail: "Truy vết các hành động quan trọng trong hệ thống.",
        icon: ClipboardCheck,
      },
    ],
  },
};

const contentAdminWorkspace = {
  eyebrow: "Khu vực biên tập",
  title: "Quản trị nội dung",
  description:
    "Tổ chức xuất bản, thư viện và các báo cáo nội dung thuộc phạm vi biên tập.",
  actions: [
    {
      href: "/admin/content",
      label: "Mở quản trị nội dung",
      detail: "Quản lý nội dung và phiên bản công khai.",
      icon: BookOpenText,
    },
    {
      href: "/notifications",
      label: "Thông báo biên tập",
      detail: "Theo dõi các thay đổi và việc cần xử lý.",
      icon: BadgeCheck,
    },
  ],
} satisfies (typeof staffWorkspaces)["ADMIN"];

function ActionGrid({ actions }: { actions: Action[] }) {
  return (
    <section
      className="grid overflow-hidden rounded-xl border border-black/10 bg-[#fbfaf7] sm:grid-cols-2"
      aria-label="Tác vụ sẵn có"
    >
      {actions.map(({ href, label, detail, icon: Icon }) => (
        <Link
          className="group min-h-40 border-b border-black/8 p-6 transition hover:bg-white sm:border-r sm:[&:nth-child(even)]:border-r-0 sm:[&:nth-last-child(-n+2)]:border-b-0"
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
  roles = [],
  accountType,
  onUpgraded,
}: {
  persona: RoleWorkspacePersona;
  roles?: readonly string[];
  accountType?: AccountType | null;
  onUpgraded?: (user: AuthUser) => void;
}) {
  const isPublic = persona === "PUBLIC";
  const workspace =
    persona === "PUBLIC"
      ? undefined
      : persona === "ADMIN" && roles.includes("CONTENT_ADMIN")
        ? contentAdminWorkspace
        : staffWorkspaces[persona];
  const title = workspace?.title ?? "Khám phá TMI";
  const description = isPublic
    ? "Tra cứu, xác minh và theo dõi hệ sinh thái chứng thư mà không cần quyền quản lý hồ sơ."
    : (workspace?.description ?? "");
  const actions = workspace?.actions ?? publicActions;
  const [primaryAction, ...secondaryActions] = actions;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <header>
        <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-primary-700">
          {isPublic ? "Không gian tra cứu" : "Công việc hôm nay"}
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">
          {title}
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-neutral-600">
          {description}
        </p>
      </header>

      {primaryAction ? (
        <section className="hero-grid-surface relative overflow-hidden rounded-2xl bg-[#151515] px-6 py-8 text-white shadow-[0_24px_70px_rgb(15_15_15/0.16)] sm:px-8 lg:grid lg:min-h-72 lg:grid-cols-[1fr_auto] lg:items-end lg:px-10 lg:py-10">
          <div className="relative z-10 max-w-2xl">
            <span className="grid size-11 place-items-center rounded-lg border border-gold-300/30 bg-gold-300/10 text-gold-300">
              {isPublic ? (
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

      {isPublic ? (
        <section className="flex gap-4 border-l-2 border-gold-300 bg-[#fbfaf7] px-5 py-4 text-sm leading-6 text-neutral-600">
          <BadgeCheck
            aria-hidden="true"
            className="mt-0.5 size-5 shrink-0 text-amber-700"
          />
          <p>
            Tài khoản của bạn chỉ hiển thị các công cụ công khai. Để tạo và nộp
            hồ sơ, hãy đăng ký đúng loại tài khoản người nộp.
          </p>
        </section>
      ) : null}

      {isPublic && accountType === "PUBLIC_USER" ? (
        <ApplicantUpgradeCard onUpgraded={onUpgraded} />
      ) : null}

      {secondaryActions.length ? (
        <ActionGrid actions={secondaryActions} />
      ) : null}
    </div>
  );
}
