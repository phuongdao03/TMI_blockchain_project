import { LayoutDashboard, Menu } from "lucide-react";
import Link from "next/link";
import type { PropsWithChildren, ReactNode } from "react";

import { BrandMark } from "@/components/layout/brand-mark";
import { DashboardContextHeader } from "@/components/layout/dashboard-context-header";
import { DashboardNavigation } from "@/components/layout/dashboard-navigation";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import type { AuthUser } from "@/lib/api/types";
import { resolveDefaultWorkspace } from "@/lib/auth/role-workspaces";
import { publicV1Features } from "@/lib/v1-features";

export function PublicShell({
  children,
  user = null,
}: PropsWithChildren<{ user?: AuthUser | null }>) {
  const publicLinks = [
    { href: "/", label: "Trang chủ" },
    {
      href: publicV1Features.publicCatalog.href,
      label: publicV1Features.publicCatalog.label,
    },
    { href: "/process", label: "Quy trình" },
    {
      href: publicV1Features.verification.href,
      label: publicV1Features.verification.label,
    },
  ];

  return (
    <div className="public-shell min-h-dvh">
      <a
        className="sr-only z-50 bg-[#fff9ef] px-4 py-3 text-[#131313] focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
        href="#noi-dung-chinh"
      >
        Bỏ qua điều hướng
      </a>
      <header className="public-header sticky top-0 z-40 border-b backdrop-blur-xl">
        <div className="mx-auto flex min-h-18 max-w-7xl items-center gap-5 px-4 sm:px-6 lg:px-8">
          <BrandMark className="mr-auto text-current" />
          <div className="hidden md:block">
            <ThemeToggle />
          </div>
          <nav
            aria-label="Điều hướng chính"
            className="flex items-center gap-1"
          >
            <div className="hidden items-center lg:flex">
              {publicLinks.map(({ href, label }) => (
                <Link
                  className="public-nav-link inline-flex min-h-11 items-center px-3 text-sm font-semibold transition-colors"
                  href={href}
                  key={href}
                >
                  {label}
                </Link>
              ))}
            </div>
            <details className="group relative lg:hidden">
              <summary className="public-menu-trigger grid size-11 cursor-pointer list-none place-items-center rounded-md border">
                <Menu aria-hidden="true" className="size-5" />
                <span className="sr-only">Mở điều hướng công khai</span>
              </summary>
              <div className="public-menu absolute top-12 right-0 z-50 grid w-64 gap-1 rounded-lg border p-2 shadow-2xl">
                <div className="mb-1 border-b border-white/10 p-1 pb-3 md:hidden">
                  <ThemeToggle />
                </div>
                {publicLinks.map(({ href, label }) => (
                  <Link
                    className="public-nav-link flex min-h-11 items-center justify-between gap-2 rounded-md px-3 py-2.5 text-sm font-semibold"
                    href={href}
                    key={href}
                  >
                    {label}
                  </Link>
                ))}
              </div>
            </details>
            {user ? (
              <Link
                className="public-workspace-link inline-flex min-h-11 shrink-0 items-center gap-2 whitespace-nowrap rounded-md border px-4 text-xs font-bold transition-colors"
                href={resolveDefaultWorkspace(user.roles)}
              >
                <LayoutDashboard aria-hidden="true" className="size-4" />
                Không gian của tôi
              </Link>
            ) : (
              <>
                <Link
                  className="public-login-link hidden min-h-11 items-center px-3 text-xs font-semibold sm:inline-flex"
                  href="/login"
                >
                  Đăng nhập
                </Link>
                <Link
                  className="hidden min-h-11 items-center rounded-md bg-primary-600 px-4 text-xs font-bold text-white transition-colors hover:bg-primary-700 sm:inline-flex"
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
      <footer className="public-footer border-t">
        <div className="public-footer-content mx-auto flex max-w-7xl flex-col gap-5 px-4 py-8 text-xs sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
          <div>
            <p className="public-footer-title font-semibold">
              Đề cử Tinh Hoa Việt
            </p>
            <p className="mt-1">Tôn vinh giá trị Việt · Thông tin minh bạch</p>
          </div>
          <div className="flex flex-wrap gap-x-5 gap-y-2">
            <Link className="public-footer-link" href="/process">
              Quy trình
            </Link>
            <Link className="public-footer-link" href="/policies">
              Chính sách
            </Link>
            <span className="public-footer-credit">TMI Group</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export function AuthShell({ children }: PropsWithChildren) {
  return (
    <div className="auth-shell auth-grid-surface flex min-h-dvh flex-col">
      <header className="public-header border-b backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 w-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <BrandMark className="text-current" />
          <ThemeToggle />
        </div>
      </header>
      <main
        aria-label="Tài khoản Đề cử Tinh Hoa Việt"
        className="flex flex-1 items-center justify-center px-4 py-8 sm:px-6 sm:py-12"
      >
        <div className="w-full max-w-[29rem]">{children}</div>
      </main>
      <footer className="mx-auto flex w-full max-w-7xl items-center justify-center gap-5 px-4 py-6 text-xs text-[#777371] sm:px-6 lg:px-8">
        <Link className="hover:text-[#e5e2e1]" href="/process">
          Quy trình
        </Link>
        <span aria-hidden="true">·</span>
        <Link className="hover:text-[#e5e2e1]" href="/policies">
          Chính sách
        </Link>
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
        Đề cử Tinh Hoa Việt
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
