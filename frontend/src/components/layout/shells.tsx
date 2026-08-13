import {
  BadgeCheck,
  LifeBuoy,
  LockKeyhole,
  Menu,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import type { PropsWithChildren, ReactNode } from "react";

import { BrandMark } from "@/components/layout/brand-mark";
import { DashboardContextHeader } from "@/components/layout/dashboard-context-header";
import { DashboardNavigation } from "@/components/layout/dashboard-navigation";
import type { AuthUser } from "@/lib/api/types";
import { resolveDefaultWorkspace } from "@/lib/auth/role-workspaces";

export function PublicShell({
  children,
  user = null,
}: PropsWithChildren<{ user?: AuthUser | null }>) {
  const publicLinks = [
    { href: "/", label: "Trang chủ" },
    { href: "/search", label: "Tìm kiếm" },
    { href: "/works", label: "Thư viện" },
    { href: "/map", label: "Bản đồ" },
    { href: "/verify", label: "Xác minh" },
    { href: "/voting", label: "Bình chọn cộng đồng" },
    { href: "/process", label: "Quy trình" },
    { href: "/policies", label: "Chính sách" },
  ] as const;

  return (
    <div className="min-h-dvh bg-[#131313] text-[#e5e2e1]">
      <a
        className="sr-only z-50 bg-[#fff9ef] px-4 py-3 text-[#131313] focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
        href="#noi-dung-chinh"
      >
        Bỏ qua điều hướng
      </a>
      <header className="sticky top-0 z-40 border-b border-white/8 bg-[#131313]/95 backdrop-blur-xl">
        <div className="mx-auto flex min-h-18 max-w-7xl items-center gap-5 px-4 sm:px-6 lg:px-8">
          <BrandMark className="mr-auto text-[#e5e2e1]" />
          <nav
            aria-label="Điều hướng chính"
            className="flex items-center gap-1"
          >
            <div className="hidden items-center lg:flex">
              {publicLinks.map(({ href, label }) => (
                <Link
                  className="inline-flex min-h-11 items-center px-3 text-xs font-semibold text-[#c8c6c5] transition-colors hover:text-[#ffb4aa]"
                  href={href}
                  key={href}
                >
                  {label}
                </Link>
              ))}
            </div>
            <details className="group relative lg:hidden">
              <summary className="grid size-11 cursor-pointer list-none place-items-center rounded-md border border-white/10 text-[#e5e2e1] hover:bg-white/5">
                <Menu aria-hidden="true" className="size-5" />
                <span className="sr-only">Mở điều hướng công khai</span>
              </summary>
              <div className="absolute top-12 right-0 z-50 grid w-56 gap-1 rounded-lg border border-white/10 bg-[#201f1f] p-2 shadow-2xl">
                {publicLinks.map(({ href, label }) => (
                  <Link
                    className="rounded-md px-3 py-2.5 text-sm font-semibold text-[#e5e2e1] hover:bg-white/5 hover:text-[#ffb4aa]"
                    href={href}
                    key={href}
                  >
                    {label}
                  </Link>
                ))}
              </div>
            </details>
            {user ? (
              <div className="flex items-center gap-2">
                <span className="hidden max-w-44 items-center gap-2 truncate rounded-full border border-white/10 px-3 py-2 text-xs font-semibold text-[#c8c6c5] md:inline-flex">
                  <UserRound
                    aria-hidden="true"
                    className="size-3.5 shrink-0 text-[#f3d675]"
                  />
                  <span className="truncate">{user.email}</span>
                </span>
                <Link
                  className="inline-flex min-h-11 items-center rounded-md border border-[#f3d675]/50 px-4 text-xs font-bold text-[#f3d675] transition-colors hover:bg-[#f3d675]/10"
                  href={resolveDefaultWorkspace(user.roles)}
                >
                  Bảng điều khiển
                </Link>
              </div>
            ) : (
              <>
                <Link
                  className="hidden min-h-11 items-center px-3 text-xs font-semibold text-[#e7bdb7] hover:text-white sm:inline-flex"
                  href="/login"
                >
                  Đăng nhập
                </Link>
                <Link
                  className="inline-flex min-h-11 items-center rounded-md bg-primary-600 px-4 text-xs font-bold text-white transition-colors hover:bg-primary-700"
                  href="/register"
                >
                  Đăng ký
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main id="noi-dung-chinh">{children}</main>
      <footer className="border-t border-white/8 bg-[#0e0e0e]">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-8 text-xs text-[#929090] sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
          <div>
            <p className="font-semibold text-[#ffb4aa]">TMI Certificate</p>
            <p className="mt-1">
              Dữ liệu bảo tồn · Trạng thái minh bạch · Xác minh độc lập
            </p>
          </div>
          <div className="flex flex-wrap gap-x-5 gap-y-2">
            <Link className="hover:text-white" href="/process">
              Quy trình
            </Link>
            <Link className="hover:text-white" href="/policies">
              Chính sách
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

export function AuthShell({ children }: PropsWithChildren) {
  return (
    <div className="auth-shell auth-grid-surface flex min-h-dvh flex-col bg-[#131313] text-[#e5e2e1]">
      <header className="border-b border-white/8 bg-[#131313]/90 backdrop-blur-xl">
        <div className="mx-auto flex min-h-18 w-full max-w-7xl items-center justify-between gap-5 px-4 sm:px-6 lg:px-8">
          <BrandMark className="text-[#e5e2e1]" />
          <p className="hidden items-center gap-2 font-mono text-[0.62rem] font-medium tracking-[0.12em] text-[#ad8883] uppercase sm:flex">
            <ShieldCheck aria-hidden="true" className="size-4" />
            Tài khoản được bảo vệ
          </p>
        </div>
      </header>
      <main
        aria-label="Tài khoản TMI"
        className="flex flex-1 items-center justify-center px-4 py-12 sm:px-6 lg:py-16"
      >
        <div className="w-full max-w-[31rem]">{children}</div>
      </main>
      <div className="mx-auto grid w-full max-w-2xl grid-cols-3 border-y border-white/8 text-center">
        {[
          { icon: LockKeyhole, label: "Bảo vệ tài khoản" },
          { icon: BadgeCheck, label: "Thông tin riêng tư" },
          { icon: LifeBuoy, label: "Hỗ trợ rõ ràng" },
        ].map(({ icon: Icon, label }) => (
          <div
            className="flex min-h-20 flex-col items-center justify-center gap-2 border-l border-white/8 first:border-l-0"
            key={label}
          >
            <Icon aria-hidden="true" className="size-4 text-[#ffb4aa]" />
            <span className="font-mono text-[0.58rem] tracking-[0.08em] text-[#929090] uppercase">
              {label}
            </span>
          </div>
        ))}
      </div>
      <footer className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-8 text-xs text-[#6f6d6c] sm:px-6 md:flex-row md:items-end md:justify-between lg:px-8">
        <div>
          <p className="text-lg font-semibold text-[#ffb4aa]">
            TMI Certificate
          </p>
          <p className="mt-1">
            Nền tảng chứng thư tài sản số có thể kiểm chứng.
          </p>
        </div>
        <p className="font-mono text-[0.58rem] tracking-[0.08em] uppercase">
          An toàn · Riêng tư · Đối chiếu minh bạch
        </p>
      </footer>
    </div>
  );
}

interface DashboardShellProps {
  children: ReactNode;
}

function WorkspaceNote() {
  return (
    <div className="border-t border-white/10 pt-5">
      <p className="font-mono text-[0.6rem] font-semibold uppercase tracking-[0.16em] text-[#ffb4aa]">
        TMI Certificate
      </p>
      <p className="mt-2 text-xs leading-5 text-slate-500">
        Công việc, hồ sơ và thông báo quan trọng trong một nơi.
      </p>
    </div>
  );
}

export function DashboardShell({ children }: DashboardShellProps) {
  return (
    <div className="min-h-dvh bg-[#121212] text-neutral-950 lg:grid lg:grid-cols-[17.25rem_minmax(0,1fr)]">
      <aside className="relative hidden min-h-dvh overflow-y-auto border-r border-white/5 bg-[#121212] p-5 text-white lg:sticky lg:top-0 lg:flex lg:h-dvh lg:flex-col">
        <div className="pointer-events-none absolute -top-32 -left-28 size-72 rounded-full bg-primary-600/15 blur-3xl" />
        <BrandMark className="relative mb-8 text-white" />
        <nav aria-label="Điều hướng bảng điều khiển">
          <DashboardNavigation />
        </nav>
        <div className="mt-auto pt-8">
          <WorkspaceNote />
        </div>
      </aside>

      <div className="dashboard-mesh min-h-dvh min-w-0">
        <header className="sticky top-0 z-20 border-b border-black/8 bg-[#fbfaf7]/92 backdrop-blur-xl">
          <DashboardContextHeader />
        </header>
        <details className="border-b border-white/10 bg-[#121212] text-white lg:hidden">
          <summary className="flex min-h-12 cursor-pointer list-none items-center gap-2 px-4 font-semibold">
            <Menu aria-hidden="true" className="size-5" />
            Mở điều hướng
          </summary>
          <DashboardNavigation className="border-t border-white/10 p-3" />
          <div className="px-3 pb-3">
            <WorkspaceNote />
          </div>
        </details>
        <main className="min-w-0 px-4 py-7 sm:px-6 lg:px-8 lg:py-10 xl:px-12">
          {children}
        </main>
      </div>
    </div>
  );
}
