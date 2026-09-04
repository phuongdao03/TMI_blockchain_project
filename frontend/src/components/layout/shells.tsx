"use client";

import {
  ArrowLeft,
  LayoutDashboard,
  LogIn,
  Menu,
  UserPlus,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type PropsWithChildren, useEffect, useRef, useState } from "react";

import { ThemeToggle } from "@/components/theme/theme-toggle";
import { resolvePublicHeaderAction } from "@/lib/auth/role-workspaces";
import { useAuthUser } from "@/lib/auth/user-context";
import type { AuthUser } from "@/lib/api/types";

import { BrandMark } from "./brand-mark";
import { DashboardContextHeader } from "./dashboard-context-header";
import { DashboardNavigation } from "./dashboard-navigation";

const publicLinks = [
  { href: "/", label: "Trang chủ" },
  { href: "/works", label: "Đề cử" },
  { href: "/process", label: "Quy trình" },
  { href: "/verify", label: "Minh bạch" },
  { href: "/guide", label: "Hướng dẫn" },
];

export function PublicShell({
  children,
  user,
}: PropsWithChildren<{ user?: AuthUser | null }>) {
  const contextUser = useAuthUser();
  const activeUser = user ?? contextUser;
  const publicHeaderAction = activeUser
    ? resolvePublicHeaderAction(activeUser.roles, activeUser.permissions ?? [])
    : null;
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const mobileNavigationRef = useRef<HTMLElement>(null);
  const firstMobileLinkRef = useRef<HTMLAnchorElement>(null);

  const closeMenu = (restoreFocus = true) => {
    setMenuOpen(false);
    if (restoreFocus) {
      requestAnimationFrame(() => menuButtonRef.current?.focus());
    }
  };

  useEffect(() => {
    if (!menuOpen) return;

    const previousOverflow = document.body.style.overflow;
    const handleDrawerKeyboard = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeMenu();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = Array.from(
        mobileNavigationRef.current?.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ) ?? [],
      );
      const first = focusable[0];
      const last = focusable.at(-1);
      if (!first || !last) return;

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleDrawerKeyboard);
    firstMobileLinkRef.current?.focus();

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleDrawerKeyboard);
    };
  }, [menuOpen]);

  return (
    <div className="public-shell">
      <a className="skip-link" href="#main-content">
        Chuyển đến nội dung chính
      </a>
      <header className="public-header">
        <BrandMark variant="public-seal" />
        <nav className="public-nav" aria-label="Điều hướng chính">
          {publicLinks.map((item) => (
            <Link key={item.href} href={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="public-header__actions">
          <ThemeToggle />
          {publicHeaderAction ? (
            <Link
              aria-label={
                publicHeaderAction.label === "Khu vực làm việc"
                  ? "Quay lại khu vực làm việc"
                  : undefined
              }
              className="button button--secondary public-header__workspace"
              href={publicHeaderAction.href}
            >
              <LayoutDashboard
                aria-hidden="true"
                className="public-header__workspace-icon"
                focusable="false"
                strokeWidth={1.75}
              />
              <span>{publicHeaderAction.label}</span>
            </Link>
          ) : (
            <>
              <Link
                className="public-header__auth-link public-header__login"
                href="/login"
              >
                <LogIn aria-hidden="true" />
                <span>Đăng nhập</span>
              </Link>
              <Link
                className="public-header__auth-link public-header__register"
                href="/register"
              >
                <UserPlus aria-hidden="true" />
                <span>Đăng ký</span>
              </Link>
            </>
          )}
          <button
            ref={menuButtonRef}
            type="button"
            className="public-header__menu"
            aria-label={menuOpen ? "Đóng menu" : "Mở menu"}
            aria-expanded={menuOpen}
            aria-controls="public-mobile-navigation"
            onClick={() => (menuOpen ? closeMenu() : setMenuOpen(true))}
          >
            {menuOpen ? (
              <X aria-hidden="true" focusable="false" strokeWidth={1.75} />
            ) : (
              <Menu aria-hidden="true" focusable="false" strokeWidth={1.75} />
            )}
          </button>
        </div>
      </header>
      {publicHeaderAction ? (
        <div
          aria-label="Quay lại khu vực làm việc"
          className="public-workspace-return"
          role="navigation"
        >
          <Link
            className="public-workspace-return__link"
            href={publicHeaderAction.href}
          >
            <ArrowLeft
              aria-hidden="true"
              focusable="false"
              strokeWidth={1.75}
            />
            <span>
              Quay lại {publicHeaderAction.label.toLocaleLowerCase("vi")}
            </span>
          </Link>
          <span className="public-workspace-return__context">
            Bạn đang xem nội dung công khai
          </span>
        </div>
      ) : null}
      {menuOpen ? (
        <div className="public-mobile-drawer">
          <button
            type="button"
            className="public-mobile-drawer__backdrop"
            aria-label="Đóng menu"
            tabIndex={-1}
            onClick={() => closeMenu()}
          />
          <nav
            ref={mobileNavigationRef}
            id="public-mobile-navigation"
            className="public-mobile-nav"
            aria-label="Điều hướng di động"
          >
            {publicLinks.map((item, index) => (
              <Link
                key={item.href}
                ref={index === 0 ? firstMobileLinkRef : undefined}
                href={item.href}
                onClick={() => closeMenu(false)}
              >
                {item.label}
              </Link>
            ))}
            {publicHeaderAction ? (
              <Link
                href={publicHeaderAction.href}
                onClick={() => closeMenu(false)}
              >
                {publicHeaderAction.label}
              </Link>
            ) : (
              <div className="public-mobile-nav__account">
                <Link
                  className="public-mobile-nav__login"
                  href="/login"
                  onClick={() => closeMenu(false)}
                >
                  <LogIn aria-hidden="true" />
                  <span>Đăng nhập</span>
                </Link>
                <Link
                  className="public-mobile-nav__register"
                  href="/register"
                  onClick={() => closeMenu(false)}
                >
                  <UserPlus aria-hidden="true" />
                  <span>Đăng ký</span>
                </Link>
              </div>
            )}
          </nav>
        </div>
      ) : null}
      <main id="main-content">{children}</main>
      <footer className="public-footer public-footer--legal">
        <div className="public-footer__identity">
          <BrandMark showCredit />
        </div>
        <nav aria-label="Liên kết cuối trang">
          <Link href="/policies">Điều khoản sử dụng</Link>
          <Link href="/policies#privacy">Chính sách quyền riêng tư</Link>
        </nav>
      </footer>
    </div>
  );
}

export function AuthShell({ children }: PropsWithChildren) {
  return (
    <div className="auth-shell">
      <header className="auth-header">
        <div className="auth-header__identity">
          <BrandMark />
        </div>
        <ThemeToggle />
      </header>
      <main id="main-content" aria-label="Khu vực tài khoản">
        {children}
      </main>
      <footer className="auth-footer">
        <Link href="/policies">Điều khoản sử dụng</Link>
        <Link href="/policies#privacy">Chính sách quyền riêng tư</Link>
      </footer>
    </div>
  );
}

export function DashboardShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const user = useAuthUser();
  const roles = user?.roles ?? [];
  const [navigationOpen, setNavigationOpen] = useState(false);
  const navigationButtonRef = useRef<HTMLButtonElement>(null);
  const navigationPanelRef = useRef<HTMLDivElement>(null);
  const navigationReturnFocusRef = useRef<HTMLElement | null>(null);

  function openNavigation(trigger: HTMLElement | null) {
    navigationReturnFocusRef.current = trigger;
    setNavigationOpen(true);
  }

  function closeNavigation({ restoreFocus = true } = {}) {
    setNavigationOpen(false);
    if (restoreFocus) {
      window.requestAnimationFrame(() =>
        navigationReturnFocusRef.current?.focus(),
      );
    }
  }

  useEffect(() => {
    if (!navigationOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    navigationPanelRef.current
      ?.querySelector<HTMLElement>("a, button")
      ?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") closeNavigation();
      if (event.key !== "Tab") return;

      const focusable = Array.from(
        navigationPanelRef.current?.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ) ?? [],
      );
      if (focusable.length === 0) return;

      const first = focusable[0]!;
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [navigationOpen]);

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <BrandMark compact />
        <DashboardNavigation roles={roles} showQuickNavigation={false} />
      </aside>
      <div className="dashboard-shell__content">
        <DashboardContextHeader
          navigationButtonRef={navigationButtonRef}
          navigationOpen={navigationOpen}
          onOpenNavigation={() => openNavigation(navigationButtonRef.current)}
          user={user}
        />
        <main className="dashboard-main" id="main-content">
          <div className="dashboard-page-stage" key={pathname}>
            {children}
          </div>
        </main>
      </div>
      <DashboardNavigation
        onOpenMenu={(trigger) => openNavigation(trigger)}
        roles={roles}
        showPrimaryNavigation={false}
      />
      {navigationOpen ? (
        <div className="dashboard-workspace-drawer">
          <button
            aria-label="Đóng điều hướng workspace"
            className="dashboard-workspace-drawer__backdrop"
            onClick={() => closeNavigation()}
            type="button"
          />
          <div
            aria-label="Điều hướng workspace"
            aria-modal="true"
            className="dashboard-workspace-drawer__panel"
            id="dashboard-workspace-navigation"
            ref={navigationPanelRef}
            role="dialog"
          >
            <div className="dashboard-workspace-drawer__header">
              <div>
                <p>Đề cử Tinh Hoa Việt</p>
                <h2>Không gian của bạn</h2>
              </div>
              <button
                aria-label="Đóng điều hướng workspace"
                onClick={() => closeNavigation()}
                type="button"
              >
                <X
                  aria-hidden="true"
                  focusable="false"
                  size={20}
                  strokeWidth={1.75}
                />
              </button>
            </div>
            <DashboardNavigation
              onNavigate={() => closeNavigation({ restoreFocus: false })}
              roles={roles}
              showQuickNavigation={false}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
