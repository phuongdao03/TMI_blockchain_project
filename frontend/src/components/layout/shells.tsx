import {
  BadgeCheck,
  Blocks,
  LockKeyhole,
  Menu,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import type { PropsWithChildren, ReactNode } from "react";

import { BrandMark } from "@/components/layout/brand-mark";
import { DashboardContextHeader } from "@/components/layout/dashboard-context-header";
import { DashboardNavigation } from "@/components/layout/dashboard-navigation";

export function PublicShell({ children }: PropsWithChildren) {
  const publicLinks = [
    { href: "/", label: "Trang chủ" },
    { href: "/tim-kiem", label: "Tìm kiếm" },
    { href: "/thu-vien", label: "Thư viện" },
    { href: "/ban-do", label: "Bản đồ" },
    { href: "/kiem-tra", label: "Xác minh" },
    { href: "/binh-chon", label: "Bình chọn cộng đồng" },
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
            <Link
              className="hidden min-h-11 items-center px-3 text-xs font-semibold text-[#e7bdb7] hover:text-white sm:inline-flex"
              href="/login"
            >
              Đăng nhập
            </Link>
            <Link
              className="inline-flex min-h-11 items-center rounded-md bg-[#ff5545] px-4 text-xs font-bold text-[#fff9ef] transition-colors hover:bg-[#ef4437]"
              href="/register"
            >
              Đăng ký
            </Link>
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
          <div className="flex flex-wrap gap-x-5 gap-y-2 font-mono text-[0.65rem] tracking-[0.08em] uppercase">
            <span>Network operational</span>
            <span>Immutable ledger</span>
            <span>Privacy policy</span>
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
            Bảo chứng bởi blockchain
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
          { icon: LockKeyhole, label: "Mã hóa AES-256" },
          { icon: Blocks, label: "Sổ cái bất biến" },
          { icon: BadgeCheck, label: "Xác minh độc lập" },
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
          Security · Privacy · Audit trail
        </p>
      </footer>
    </div>
  );
}

interface DashboardShellProps {
  children: ReactNode;
}

function VerificationStatus() {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3.5">
      <p className="flex items-center gap-2 text-xs font-semibold text-emerald-300">
        <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_12px_#34d399]" />
        Hệ thống xác minh sẵn sàng
      </p>
      <p className="mt-1.5 text-xs leading-5 text-slate-500">
        Môi trường thử nghiệm
      </p>
    </div>
  );
}

export function DashboardShell({ children }: DashboardShellProps) {
  return (
    <div className="dashboard-mesh min-h-dvh bg-neutral-50 text-neutral-950 lg:grid lg:grid-cols-[18.5rem_minmax(0,1fr)]">
      <aside className="relative hidden min-h-dvh overflow-hidden border-r border-white/5 bg-ink-950 p-5 text-white lg:flex lg:flex-col">
        <div className="pointer-events-none absolute -top-32 -left-28 size-72 rounded-full bg-primary-600/15 blur-3xl" />
        <BrandMark className="relative mb-10 text-white" />
        <p className="mb-3 px-3 text-[0.68rem] font-bold uppercase tracking-[0.18em] text-slate-500">
          Không gian làm việc
        </p>
        <nav aria-label="Điều hướng bảng điều khiển">
          <DashboardNavigation />
        </nav>
        <div className="mt-auto pt-8">
          <VerificationStatus />
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 border-b border-neutral-200/80 bg-white/90 backdrop-blur-xl">
          <DashboardContextHeader />
        </header>
        <details className="border-b border-white/10 bg-ink-950 text-white lg:hidden">
          <summary className="flex min-h-12 cursor-pointer list-none items-center gap-2 px-4 font-semibold">
            <Menu aria-hidden="true" className="size-5" />
            Mở điều hướng
          </summary>
          <DashboardNavigation className="border-t border-white/10 p-3" />
          <div className="px-3 pb-3">
            <VerificationStatus />
          </div>
        </details>
        <main className="min-w-0 px-4 py-7 sm:px-6 lg:px-8 lg:py-9 xl:px-10">
          {children}
        </main>
      </div>
    </div>
  );
}
