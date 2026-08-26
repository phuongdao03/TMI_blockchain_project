"use client";

import { LayoutDashboard, Menu, X } from "lucide-react";
import Link from "next/link";
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
];

export function PublicShell({
  children,
  user,
}: PropsWithChildren<{ user?: AuthUser | null }>) {
  const contextUser = useAuthUser();
  const activeUser = user ?? contextUser;
  const publicHeaderAction = activeUser
    ? resolvePublicHeaderAction(activeUser.roles)
    : null;
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
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
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMenu();
    };

    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", closeOnEscape);
    firstMobileLinkRef.current?.focus();

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", closeOnEscape);
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
              className="button button--secondary public-header__workspace"
              href={publicHeaderAction.href}
            >
              <LayoutDashboard
                aria-hidden="true"
                className="public-header__workspace-icon"
              />
              <span>{publicHeaderAction.label}</span>
            </Link>
          ) : (
            <>
              <Link
                className="public-header__auth-link public-header__login"
                href="/login"
              >
                Đăng nhập
              </Link>
              <Link
                className="public-header__auth-link public-header__register"
                href="/register"
              >
                Đăng ký
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
            {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
          </button>
        </div>
      </header>
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
                <Link href="/login" onClick={() => closeMenu(false)}>
                  Đăng nhập
                </Link>
                <Link href="/register" onClick={() => closeMenu(false)}>
                  Đăng ký
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
  const user = useAuthUser();
  const roles = user?.roles ?? [];

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <BrandMark compact />
        <DashboardNavigation roles={roles} />
      </aside>
      <div className="dashboard-shell__content">
        <DashboardContextHeader user={user} />
        <main className="dashboard-main" id="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
