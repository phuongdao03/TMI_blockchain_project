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

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    href: "/tim-kiem",
    label: "Tìm tài sản số",
    detail: "Tra cứu theo mã, tên hoặc tổ chức phát hành.",
    icon: Search,
  },
  {
    href: "/thu-vien",
    label: "Thư viện chứng thư",
    detail: "Khám phá các tài sản đã được công khai.",
    icon: BookOpenText,
  },
  {
    href: "/ban-do",
    label: "Bản đồ xác lập",
    detail: "Xem hệ sinh thái tài sản theo khu vực.",
    icon: Map,
  },
  {
    href: "/kiem-tra",
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
    eyebrow: "Review workspace",
    title: "Hàng đợi thẩm định",
    description:
      "Tập trung vào hồ sơ được phân công, tiêu chí 5T và các mốc SLA cần xử lý.",
    actions: [
      {
        href: "/tham-dinh",
        label: "Mở hàng đợi thẩm định",
        detail: "Xem phân công và tiếp tục phiên đánh giá.",
        icon: ClipboardCheck,
      },
      {
        href: "/thong-bao",
        label: "Thông báo công việc",
        detail: "Theo dõi thay đổi phân công và nhắc hạn.",
        icon: BadgeCheck,
      },
    ],
  },
  COUNCIL: {
    eyebrow: "Council workspace",
    title: "Phiên xét duyệt Hội đồng",
    description:
      "Rà soát chương trình họp, công khai xung đột lợi ích và biểu quyết theo phiên.",
    actions: [
      {
        href: "/hoi-dong",
        label: "Mở phiên Hội đồng",
        detail: "Xem agenda, biên bản và quyết định đang chờ.",
        icon: Landmark,
      },
      {
        href: "/thong-bao",
        label: "Thông báo phiên họp",
        detail: "Theo dõi lịch và thay đổi của Hội đồng.",
        icon: BadgeCheck,
      },
    ],
  },
  ADMIN: {
    eyebrow: "Operations workspace",
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
        href: "/thong-bao",
        label: "Thông báo vận hành",
        detail: "Theo dõi các sự kiện và ngoại lệ thuộc phạm vi của bạn.",
        icon: BadgeCheck,
      },
    ],
  },
  SUPER_ADMIN: {
    eyebrow: "System workspace",
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
  eyebrow: "Content workspace",
  title: "Quản trị nội dung",
  description:
    "Tổ chức xuất bản, thư viện và các báo cáo nội dung thuộc phạm vi biên tập.",
  actions: [
    {
      href: "/admin/noi-dung",
      label: "Mở quản trị nội dung",
      detail: "Quản lý nội dung và phiên bản công khai.",
      icon: BookOpenText,
    },
    {
      href: "/thong-bao",
      label: "Thông báo biên tập",
      detail: "Theo dõi các thay đổi và việc cần xử lý.",
      icon: BadgeCheck,
    },
  ],
} satisfies (typeof staffWorkspaces)["ADMIN"];

function ActionGrid({ actions }: { actions: Action[] }) {
  return (
    <section className="grid gap-4 sm:grid-cols-2" aria-label="Tác vụ sẵn có">
      {actions.map(({ href, label, detail, icon: Icon }) => (
        <Link
          className="group min-h-40 rounded-2xl border border-neutral-200 bg-white p-5 shadow-[0_1px_2px_rgb(15_23_42/0.03)] transition hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-lg hover:shadow-primary-950/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
          href={href}
          key={href}
        >
          <span className="grid size-11 place-items-center rounded-xl bg-primary-50 text-primary-700">
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

  return (
    <div className="mx-auto max-w-6xl space-y-7">
      <header className="rounded-3xl border border-white/5 bg-ink-950 px-6 py-8 text-white shadow-2xl shadow-slate-950/10 sm:px-8 sm:py-10">
        <span className="grid size-12 place-items-center rounded-2xl border border-gold-300/30 bg-gold-300/10 text-gold-300">
          {isPublic ? (
            <Sparkles aria-hidden="true" className="size-6" />
          ) : (
            <ShieldCheck aria-hidden="true" className="size-6" />
          )}
        </span>
        <p className="mt-6 text-xs font-bold uppercase tracking-[0.18em] text-gold-300">
          {isPublic ? "Discovery workspace" : workspace?.eyebrow}
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
          {title}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
          {description}
        </p>
      </header>

      {isPublic ? (
        <Card className="border-gold-300/25 bg-amber-50/60">
          <CardHeader>
            <BadgeCheck aria-hidden="true" className="size-6 text-amber-700" />
            <CardTitle>Không gian tra cứu an toàn</CardTitle>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-neutral-600">
            Tài khoản của bạn chỉ hiển thị các công cụ công khai. Để tạo và nộp
            hồ sơ, hãy đăng ký đúng loại tài khoản người nộp.
          </CardContent>
        </Card>
      ) : null}

      {isPublic && accountType === "PUBLIC_USER" ? (
        <ApplicantUpgradeCard onUpgraded={onUpgraded} />
      ) : null}

      <ActionGrid actions={actions} />
    </div>
  );
}
