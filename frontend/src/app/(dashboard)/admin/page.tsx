import {
  BookOpenText,
  ChartNoAxesCombined,
  ChevronRight,
  ClipboardCheck,
  FilePenLine,
  FileClock,
  UsersRound,
} from "lucide-react";
import Link from "next/link";

import { RoleGate } from "@/components/auth/role-gate";
import { OperationsDashboard } from "@/components/admin/operations-dashboard";

const modules = [
  {
    href: "/admin/employees",
    title: "Nhân sự",
    description:
      "Quản lý tài khoản, hồ sơ nhân viên và quyền chấm công tại một nơi.",
    icon: UsersRound,
    tone: "bg-primary-50 text-primary-700",
  },
  {
    href: "/admin/certificate-updates",
    title: "Cập nhật bằng xác lập",
    description:
      "Xem xét yêu cầu điều chỉnh và theo dõi việc phát hành phiên bản thay thế.",
    icon: FilePenLine,
    tone: "bg-rose-50 text-rose-700",
  },
  {
    href: "/admin/dashboard",
    title: "Theo dõi vận hành",
    description:
      "Nắm tiến độ hồ sơ, thanh toán, phát hành và những việc cần xử lý.",
    icon: ChartNoAxesCombined,
    tone: "bg-amber-50 text-amber-700",
  },
  {
    href: "/admin/content",
    title: "Nội dung công khai",
    description:
      "Kiểm duyệt bài viết, trang thông tin và các nội dung đang hiển thị.",
    icon: BookOpenText,
    tone: "bg-emerald-50 text-emerald-700",
  },
  {
    href: "/reviews",
    title: "Hàng đợi thẩm định",
    description: "Xem hồ sơ được giao và tiếp tục các phiếu đánh giá còn lại.",
    icon: ClipboardCheck,
    tone: "bg-sky-50 text-sky-700",
  },
  {
    href: "/admin/audit",
    title: "Lịch sử thay đổi",
    description:
      "Xem lại các mốc quan trọng để giải thích và đối chiếu khi cần.",
    icon: FileClock,
    tone: "bg-slate-100 text-slate-700",
  },
] as const;

export default function AdminPortalPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <div className="mx-auto max-w-7xl space-y-8">
        <section
          aria-labelledby="admin-start-title"
          className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-6"
        >
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            Công việc hôm nay
          </p>
          <h1 className="mt-2 text-2xl font-bold" id="admin-start-title">
            Bắt đầu xử lý hồ sơ
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
            Đi theo thứ tự từ tiếp nhận, thẩm định đến phát hành. Mỗi mục mở
            đúng khu vực xử lý hiện có.
          </p>
          <nav aria-label="Quy trình hồ sơ" className="mt-5">
            <ol className="divide-y divide-[var(--theme-border)] sm:grid sm:grid-cols-2 sm:gap-2 sm:divide-y-0 xl:grid-cols-4">
              {(
                [
                  [
                    "01",
                    "Tiếp nhận và phân công",
                    "Giao hồ sơ mới cho người thẩm định",
                    "/admin/reviews",
                  ],
                  [
                    "02",
                    "Theo dõi thẩm định",
                    "Xem tiến độ và các trường hợp cần chú ý",
                    "/admin/dashboard",
                  ],
                  [
                    "03",
                    "Quyết định phí",
                    "Chọn thu phí hoặc miễn phí sau khi duyệt",
                    "/admin/payments",
                  ],
                  [
                    "04",
                    "Hoàn tất phát hành",
                    "Kiểm tra bằng xác lập và công bố",
                    "/admin/certificates",
                  ],
                ] as const
              ).map(([number, title, description, href]) => (
                <li key={href}>
                  <Link
                    className="flex h-full min-h-16 items-center gap-3 py-2.5 transition-colors hover:text-primary-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary-600 sm:min-h-28 sm:items-start sm:rounded-xl sm:border sm:border-[var(--theme-border)] sm:bg-[var(--theme-elevated)] sm:p-4 sm:hover:border-primary-300"
                    href={href}
                  >
                    <span
                      aria-hidden="true"
                      className="font-mono text-sm font-bold text-primary-700"
                    >
                      {number}
                    </span>
                    <span>
                      <strong className="block text-sm text-[var(--theme-text)]">
                        {title}
                      </strong>
                      <span className="mt-1 block text-xs leading-5 text-[var(--theme-muted)]">
                        {description}
                      </span>
                    </span>
                    <ChevronRight
                      aria-hidden="true"
                      className="ml-auto size-4 shrink-0 text-[var(--theme-muted)] sm:hidden"
                    />
                  </Link>
                </li>
              ))}
            </ol>
          </nav>
        </section>
        <section aria-labelledby="admin-priority-title">
          <div className="mb-5">
            <p className="text-sm font-bold uppercase tracking-[0.16em] text-primary-700">
              Ưu tiên hôm nay
            </p>
            <h2
              className="mt-2 text-2xl font-bold text-neutral-950"
              id="admin-priority-title"
            >
              Việc đang cần chú ý
            </h2>
          </div>
          <OperationsDashboard showHeader={false} />
        </section>

        <section aria-labelledby="admin-modules-title">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.16em] text-primary-700">
                Điểm làm việc
              </p>
              <h2
                id="admin-modules-title"
                className="mt-2 text-2xl font-bold text-neutral-950"
              >
                Chọn việc bạn muốn xử lý
              </h2>
            </div>
            <Link
              className="text-sm font-bold text-primary-700 underline-offset-4 hover:underline"
              href="/admin/employees"
            >
              Quản lý đội ngũ →
            </Link>
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {modules.map(({ href, title, description, icon: Icon, tone }) => (
              <Link
                className="group rounded-2xl border border-neutral-200 bg-white p-5 transition hover:-translate-y-0.5 hover:border-primary-300 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                href={href}
                key={href}
              >
                <span className={`inline-flex rounded-xl p-3 ${tone}`}>
                  <Icon aria-hidden="true" className="size-5" />
                </span>
                <h3 className="mt-5 text-lg font-bold text-neutral-950">
                  {title}
                </h3>
                <p className="mt-2 min-h-14 text-sm leading-6 text-neutral-600">
                  {description}
                </p>
                <span className="mt-5 inline-flex text-sm font-bold text-primary-700">
                  Mở khu vực này →
                </span>
              </Link>
            ))}
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <article className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
            <h2 className="text-lg font-bold text-amber-950">
              Nguyên tắc an toàn
            </h2>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-amber-900">
              <li>• Chỉ mời người đã được xác minh và có công việc cụ thể.</li>
              <li>
                • Mỗi lời mời chỉ mở phần việc cần thiết và có thể thu hồi ngay.
              </li>
              <li>
                • Khóa tài khoản sẽ dừng các phiên đang hoạt động để bảo vệ dữ
                liệu.
              </li>
            </ul>
          </article>
          <article className="rounded-2xl border border-neutral-200 bg-white p-6">
            <h2 className="text-lg font-bold text-neutral-950">Cần hỗ trợ?</h2>
            <p className="mt-3 text-sm leading-6 text-neutral-600">
              Nếu không thấy khu vực cần làm, hãy liên hệ người phụ trách tài
              khoản của tổ chức để được kiểm tra lời mời và phạm vi công việc.
            </p>
          </article>
        </section>
      </div>
    </RoleGate>
  );
}
