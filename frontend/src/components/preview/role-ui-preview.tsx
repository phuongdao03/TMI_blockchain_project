"use client";

import {
  BadgeCheck,
  BookOpenText,
  BriefcaseBusiness,
  CircleAlert,
  Eye,
  Files,
  MapPin,
  WalletCards,
} from "lucide-react";
import Link from "next/link";

import { BrandMark } from "@/components/layout/brand-mark";
import { DashboardNavigation } from "@/components/layout/dashboard-navigation";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import type { AuthUser } from "@/lib/api/types";
import type { WorkspacePersona } from "@/lib/auth/role-workspaces";
import { AuthUserProvider } from "@/lib/auth/user-context";
import { previewScreenFor, type PreviewScreen } from "./preview-screens";

const roleOptions: ReadonlyArray<{
  role: WorkspacePersona;
  label: string;
  home: string;
}> = [
  { role: "VIEWER", label: "Khách xem", home: "/dashboard" },
  { role: "USER", label: "Nhân viên / người dùng", home: "/dashboard" },
  { role: "MODERATOR", label: "Moderator", home: "/work-allocations" },
  { role: "SUPER_ADMIN", label: "Super Admin", home: "/admin" },
];

const roleTitles: Record<WorkspacePersona, string> = {
  VIEWER: "Không gian tra cứu",
  USER: "Không gian người dùng",
  MODERATOR: "Không gian kiểm duyệt",
  SUPER_ADMIN: "Không gian quản trị",
};

function previewHref(role: WorkspacePersona, path: string) {
  return `/ui-preview?role=${role}&path=${encodeURIComponent(path)}`;
}

function RoleHome({ role }: { role: WorkspacePersona }) {
  if (role === "VIEWER") {
    return (
      <>
        <PageHeading
          eyebrow="Khám phá"
          title="Đề cử Tinh Hoa Việt"
          description="Tra cứu tác phẩm, câu chuyện và những giá trị Việt được giới thiệu trên hệ thống."
        />
        <section
          className="grid gap-4 md:grid-cols-3"
          aria-label="Tổng quan nội dung"
        >
          <PreviewCard
            icon={BookOpenText}
            title="Tác phẩm nổi bật"
            value="Khám phá thư viện"
            detail="Tìm kiếm theo tên, chủ đề và danh mục."
            href={previewHref(role, "/works")}
          />
          <PreviewCard
            icon={BadgeCheck}
            title="Xác minh chứng thư"
            value="Tra cứu công khai"
            detail="Kiểm tra thông tin phát hành và trạng thái."
            href={previewHref(role, "/verify")}
          />
          <PreviewCard
            icon={Files}
            title="Hồ sơ chương trình"
            value="Thông tin minh bạch"
            detail="Theo dõi quy trình và tiêu chí xét duyệt."
          />
        </section>
        <InfoPanel
          title="Bắt đầu tra cứu"
          detail="Các mục điều hướng và nội dung công khai nằm trong thanh bên. Đây là dữ liệu minh họa cho bản xem giao diện."
        />
      </>
    );
  }

  if (role === "USER") {
    return (
      <>
        <PageHeading
          eyebrow="Trung tâm hồ sơ"
          title="Việc cần làm"
          description="Theo dõi tiến độ hồ sơ, cập nhật cần xử lý và chứng thư đã phát hành."
        />
        <section
          className="grid gap-4 sm:grid-cols-3"
          aria-label="Tổng quan hồ sơ"
        >
          <PreviewCard
            icon={Files}
            title="Đang xử lý"
            value="02 hồ sơ"
            detail="Hồ sơ đã gửi và đang được tiếp nhận."
            href={previewHref(role, "/dossiers")}
          />
          <PreviewCard
            icon={CircleAlert}
            title="Cần bổ sung"
            value="01 hồ sơ"
            detail="Có yêu cầu cập nhật tài liệu."
            href={previewHref(role, "/dossiers")}
          />
          <PreviewCard
            icon={BadgeCheck}
            title="Đã hoàn tất"
            value="03 chứng thư"
            detail="Chứng thư đã được phát hành."
            href={previewHref(role, "/certificates")}
          />
        </section>
        <InfoPanel
          title="Hồ sơ gần đây"
          detail="Mẫu xem trước · Bộ nhận diện thương hiệu · Đang thẩm định"
        />
      </>
    );
  }

  if (role === "MODERATOR") {
    return (
      <>
        <PageHeading
          eyebrow="Công việc hôm nay"
          title="Hàng đợi thẩm định"
          description="Tập trung vào hồ sơ được phân công, tiêu chí đánh giá và thời hạn xử lý."
        />
        <section
          className="grid gap-4 sm:grid-cols-3"
          aria-label="Tổng quan thẩm định"
        >
          <PreviewCard
            icon={Files}
            title="Được phân công"
            value="04 hồ sơ"
            detail="Hồ sơ chờ đọc và đánh giá."
            href={previewHref(role, "/work-allocations")}
          />
          <PreviewCard
            icon={CircleAlert}
            title="Cần ưu tiên"
            value="01 hồ sơ"
            detail="Thời hạn xử lý đang đến gần."
            href={previewHref(role, "/work-allocations")}
          />
          <PreviewCard
            icon={BadgeCheck}
            title="Đã hoàn tất"
            value="08 hồ sơ"
            detail="Đánh giá đã gửi trong kỳ."
          />
        </section>
        <InfoPanel
          title="Công việc được giao"
          detail="Mẫu xem trước · Hồ sơ đề cử tác phẩm · 3 tài liệu · Hạn xử lý 28/09/2026"
        />
      </>
    );
  }

  return (
    <>
      <PageHeading
        eyebrow="Điều hành toàn hệ thống"
        title="Bảng điều hành"
        description="Theo dõi hoạt động, nhân sự, công việc và các ngoại lệ cần xử lý."
      />
      <section
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Chỉ số điều hành"
      >
        <PreviewCard
          icon={Files}
          title="Hồ sơ đang xử lý"
          value="24"
          detail="Trên các giai đoạn tiếp nhận."
          href={previewHref(role, "/admin/dashboard")}
        />
        <PreviewCard
          icon={CircleAlert}
          title="Cần ưu tiên"
          value="03"
          detail="Ngoại lệ cần xem xét."
        />
        <PreviewCard
          icon={BriefcaseBusiness}
          title="Nhân sự hoạt động"
          value="18"
          detail="Phân bổ theo phòng ban."
          href={previewHref(role, "/admin/employees")}
        />
        <PreviewCard
          icon={WalletCards}
          title="Kỳ lương"
          value="Bản nháp"
          detail="Kỳ hiện tại chưa xác nhận."
          href={previewHref(role, "/admin/payroll")}
        />
      </section>
      <section
        className="grid gap-4 md:grid-cols-2"
        aria-label="Quản trị nhân sự"
      >
        <InfoPanel
          icon={MapPin}
          title="Địa điểm và chấm công"
          detail="Quản lý địa điểm làm việc, chính sách vị trí và yêu cầu cần xem xét."
        />
        <InfoPanel
          icon={BriefcaseBusiness}
          title="Phân công công việc"
          detail="Tạo đầu việc, chọn tài liệu liên quan và phân công thành viên."
        />
      </section>
    </>
  );
}

function PageHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <header className="mb-6 border-b border-[var(--theme-line)] pb-5">
      <p className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--theme-accent)]">
        {eyebrow}
      </p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--theme-ink)] sm:text-3xl">
        {title}
      </h1>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--theme-muted)]">
        {description}
      </p>
    </header>
  );
}

function PreviewCard({
  icon: Icon,
  title,
  value,
  detail,
  href,
}: {
  icon: typeof Files;
  title: string;
  value: string;
  detail: string;
  href?: string;
}) {
  const content = (
    <>
      <div className="flex items-center gap-2 text-xs font-semibold text-[var(--theme-muted)]">
        <Icon
          aria-hidden="true"
          className="size-4 text-[var(--theme-accent)]"
        />
        {title}
      </div>
      <p className="mt-4 text-xl font-semibold text-[var(--theme-ink)]">
        {value}
      </p>
      <p className="mt-1 text-xs leading-5 text-[var(--theme-muted)]">
        {detail}
      </p>
    </>
  );
  const className =
    "block rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4";
  return href ? (
    <Link
      className={`${className} transition hover:border-[var(--theme-accent)] hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]`}
      href={href}
    >
      {content}
    </Link>
  ) : (
    <article className={className}>{content}</article>
  );
}

function InfoPanel({
  icon: Icon = Eye,
  title,
  detail,
}: {
  icon?: typeof Eye;
  title: string;
  detail: string;
}) {
  return (
    <section className="mt-5 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5">
      <h2 className="flex items-center gap-2 text-base font-semibold text-[var(--theme-ink)]">
        <Icon
          aria-hidden="true"
          className="size-4 text-[var(--theme-accent)]"
        />
        {title}
      </h2>
      <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
        {detail}
      </p>
    </section>
  );
}

function ScreenPreview({ screen }: { screen: PreviewScreen }) {
  return (
    <>
      <PageHeading
        eyebrow={screen.eyebrow}
        title={screen.title}
        description={screen.description}
      />
      <section
        aria-label={`Danh sách ${screen.title.toLowerCase()}`}
        className="overflow-hidden rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)]"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--theme-border)] px-4 py-3 sm:px-5">
          <h2 className="text-sm font-semibold text-[var(--theme-ink)]">
            Danh sách minh họa
          </h2>
          <span className="text-xs text-[var(--theme-muted)]">
            {screen.rows.length} bản ghi mẫu
          </span>
        </div>
        <div className="grid gap-3 p-3 sm:hidden">
          {screen.rows.map((row) => (
            <article
              className="rounded-lg border border-[var(--theme-border)] bg-[var(--theme-bg)] p-3"
              key={row.join("|")}
            >
              {row.map((cell, index) => (
                <div
                  className="grid grid-cols-[minmax(0,6rem)_minmax(0,1fr)] gap-3 py-1.5 text-sm"
                  key={`${index}-${cell}`}
                >
                  <span className="text-[var(--theme-muted)]">
                    {screen.columns[index]}
                  </span>
                  <span className="min-w-0 break-words font-medium text-[var(--theme-text)]">
                    {cell}
                  </span>
                </div>
              ))}
            </article>
          ))}
        </div>
        <div className="hidden overflow-x-auto sm:block">
          <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
            <thead className="bg-[var(--theme-elevated)] text-[var(--theme-muted)]">
              <tr>
                {screen.columns.map((column) => (
                  <th
                    className="px-4 py-3 font-semibold sm:px-5"
                    key={column}
                    scope="col"
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {screen.rows.map((row) => (
                <tr
                  className="border-t border-[var(--theme-border)] text-[var(--theme-text)]"
                  key={row.join("|")}
                >
                  {row.map((cell, index) => (
                    <td
                      className="px-4 py-3.5 align-top sm:px-5"
                      key={`${index}-${cell}`}
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <InfoPanel
        title="Xem trước chức năng"
        detail="Màn hình này dùng dữ liệu minh họa để xem bố cục và điều hướng. Các thao tác nghiệp vụ được kiểm tra trong môi trường có tài khoản phù hợp."
      />
    </>
  );
}

export function RoleUiPreview({
  role,
  path,
}: {
  role: WorkspacePersona;
  path?: string;
}) {
  const user: AuthUser = {
    id: `local-preview-${role.toLowerCase()}`,
    email: `${role.toLowerCase()}@preview.local`,
    roles: [role],
    accountType: null,
  };
  const defaultPath =
    roleOptions.find((option) => option.role === role)?.home ?? "/dashboard";
  const screen = previewScreenFor(role, path);
  const activePath = screen ? path : defaultPath;

  return (
    <AuthUserProvider user={user}>
      <div className="ui-preview-shell min-h-dvh bg-[var(--theme-bg)] text-[var(--theme-text)]">
        <div className="border-b border-[var(--theme-border)] bg-[var(--theme-elevated)] px-4 py-2 text-sm text-[var(--theme-text)]">
          <p className="mx-auto flex max-w-7xl items-center gap-2">
            <Eye aria-hidden="true" className="size-4 shrink-0" />
            <span>
              <strong>Chế độ xem giao diện.</strong> Không đăng nhập, không gọi
              API; số liệu bên dưới chỉ để minh họa.
            </span>
          </p>
        </div>

        <header className="border-b border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-4 sm:px-6">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center justify-between gap-4">
              <BrandMark compact />
              <ThemeToggle />
            </div>
            <nav
              aria-label="Chọn giao diện vai trò"
              className="flex gap-2 overflow-x-auto pb-1"
            >
              {roleOptions.map((option) => (
                <Link
                  aria-current={option.role === role ? "page" : undefined}
                  className={`inline-flex min-h-10 shrink-0 items-center rounded-lg border px-3 text-sm font-medium transition ${option.role === role ? "border-primary-700 bg-primary-700 text-white" : "border-[var(--theme-border)] text-[var(--theme-ink)] hover:bg-[var(--theme-bg)]"}`}
                  href={`/ui-preview?role=${option.role}`}
                  key={option.role}
                >
                  {option.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        <div className="mx-auto grid max-w-[96rem] gap-4 p-4 md:grid-cols-[17.5rem_minmax(0,1fr)] md:gap-0 md:p-0">
          <aside className="ui-preview-sidebar max-h-64 overflow-y-auto rounded-xl border p-3 md:sticky md:top-0 md:h-dvh md:max-h-dvh md:rounded-none md:border-y-0 md:border-l-0 md:border-r md:p-4">
            <p className="mb-3 px-2 text-xs font-semibold">
              {roleTitles[role]}
            </p>
            <DashboardNavigation
              previewPathname={activePath}
              previewRole={role}
              roles={[role]}
              showQuickNavigation={false}
            />
          </aside>

          <main
            className="min-w-0 px-0 py-2 sm:px-3 md:px-6 md:py-7 lg:px-9"
            id="main-content"
          >
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--theme-line)] pb-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--theme-muted)]">
                  {roleTitles[role]}
                </p>
                <p className="mt-1 text-lg font-semibold text-[var(--theme-ink)]">
                  {screen?.title ??
                    (role === "VIEWER" || role === "USER"
                      ? "Tổng quan"
                      : role === "MODERATOR"
                        ? "Công việc được giao"
                        : "Quản trị hệ thống")}
                </p>
              </div>
              <span className="rounded-full border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 py-1.5 text-xs font-medium text-[var(--theme-text)]">
                Xem thử · {role}
              </span>
            </div>
            {screen ? (
              <ScreenPreview screen={screen} />
            ) : (
              <RoleHome role={role} />
            )}
          </main>
        </div>
      </div>
    </AuthUserProvider>
  );
}
