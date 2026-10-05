"use client";

import {
  ArrowLeft,
  BookOpen,
  FileText,
  LayoutDashboard,
  LogIn,
  Menu,
  Mail,
  MapPin,
  Music2,
  Phone,
  Search,
  UserPlus,
  X,
} from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { type PropsWithChildren, useEffect, useRef, useState } from "react";

import { ThemeToggle } from "@/components/theme/theme-toggle";
import { PwaInstallButton } from "@/components/pwa/pwa-install-button";
import { LogoutButton } from "@/components/auth/logout-button";
import { IconFrame } from "@/components/ui/icon-frame";
import { resolvePublicHeaderAction } from "@/lib/auth/role-workspaces";
import { useAuthUser } from "@/lib/auth/user-context";
import type { AuthUser } from "@/lib/api/types";

import { BrandMark } from "./brand-mark";
import { DashboardContextHeader } from "./dashboard-context-header";
import { DashboardNavigation } from "./dashboard-navigation";

const publicLinks = [
  { href: "/", label: "Trang chủ" },
  { href: "/search", label: "Tìm đề cử" },
  { href: "/works", label: "Danh sách đề cử" },
  { href: "/process", label: "Quy trình" },
  { href: "/verify", label: "Tra cứu bằng xác lập" },
  { href: "/guide", label: "Hướng dẫn" },
];

export function PublicShell({
  children,
  user,
}: PropsWithChildren<{ user?: AuthUser | null }>) {
  const pathname = usePathname();
  const contextUser = useAuthUser();
  const activeUser = user ?? contextUser;
  const publicHeaderAction = activeUser
    ? resolvePublicHeaderAction(activeUser.roles, activeUser.permissions ?? [])
    : null;
  const quickLinks = publicHeaderAction
    ? [
        ...(publicHeaderAction.href === "/dossiers"
          ? [{ href: "/dashboard", label: "Tổng quan", icon: LayoutDashboard }]
          : []),
        {
          href: publicHeaderAction.href,
          label:
            publicHeaderAction.href === "/dossiers"
              ? "Hồ sơ của tôi"
              : publicHeaderAction.label,
          icon:
            publicHeaderAction.href === "/dossiers"
              ? FileText
              : LayoutDashboard,
        },
        { href: "/search", label: "Tìm đề cử", icon: Search },
        { href: "/works", label: "Thư viện đề cử", icon: BookOpen },
      ]
    : [];
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const menuReturnFocusRef = useRef<HTMLButtonElement | null>(null);
  const mobileNavigationRef = useRef<HTMLElement>(null);
  const firstMobileLinkRef = useRef<HTMLAnchorElement>(null);

  const closeMenu = (restoreFocus = true) => {
    setMenuOpen(false);
    if (restoreFocus) {
      requestAnimationFrame(() =>
        (menuReturnFocusRef.current ?? menuButtonRef.current)?.focus(),
      );
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
    <div
      className={
        publicHeaderAction
          ? "public-shell public-shell--workspace"
          : "public-shell"
      }
    >
      <a className="skip-link" href="#main-content">
        Chuyển đến nội dung chính
      </a>
      <header className="public-header">
        <BrandMark />
        <nav className="public-nav" aria-label="Điều hướng chính">
          {publicLinks.map((item) => {
            const active =
              item.href === "/"
                ? pathname === item.href
                : pathname === item.href ||
                  pathname.startsWith(`${item.href}/`);
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className="public-nav__link"
                key={item.href}
                href={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="public-header__actions">
          <PwaInstallButton />
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
            onClick={(event) => {
              if (menuOpen) closeMenu();
              else {
                menuReturnFocusRef.current = event.currentTarget;
                setMenuOpen(true);
              }
            }}
          >
            {menuOpen ? (
              <X aria-hidden="true" focusable="false" strokeWidth={1.75} />
            ) : (
              <Menu aria-hidden="true" focusable="false" strokeWidth={1.75} />
            )}
          </button>
        </div>
      </header>
      {!publicHeaderAction ? (
        <nav aria-label="Truy cập tài khoản" className="public-mobile-auth">
          <Link className="public-mobile-auth__login" href="/login">
            <LogIn aria-hidden="true" />
            Đăng nhập
          </Link>
          <Link className="public-mobile-auth__register" href="/register">
            <UserPlus aria-hidden="true" />
            Tạo tài khoản
          </Link>
        </nav>
      ) : null}
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
            {publicLinks.map((item, index) => {
              const active =
                item.href === "/"
                  ? pathname === item.href
                  : pathname === item.href ||
                    pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  aria-current={active ? "page" : undefined}
                  className="public-mobile-nav__link"
                  key={item.href}
                  ref={index === 0 ? firstMobileLinkRef : undefined}
                  href={item.href}
                  onClick={() => closeMenu(false)}
                >
                  {item.label}
                </Link>
              );
            })}
            <Link href="/install" onClick={() => closeMenu(false)}>
              Cài ứng dụng
            </Link>
            {publicHeaderAction ? (
              <Link
                href={publicHeaderAction.href}
                onClick={() => closeMenu(false)}
              >
                {publicHeaderAction.label}
              </Link>
            ) : (
              <div
                aria-label="Tài khoản"
                className="public-mobile-nav__account"
                role="group"
              >
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
      {publicHeaderAction ? (
        <nav
          aria-label="Điều hướng nhanh"
          className={`dashboard-mobile-navigation public-workspace-navigation${quickLinks.length === 3 ? " public-workspace-navigation--compact" : ""}`}
        >
          {quickLinks.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={`dashboard-mobile-navigation__link${
                  active ? " dashboard-mobile-navigation__link--active" : ""
                }`}
                href={item.href}
                key={item.href}
              >
                <IconFrame
                  className="dashboard-mobile-navigation__icon"
                  icon={item.icon}
                  size="sm"
                  tone={active ? "brand" : "neutral"}
                />
                <span className="dashboard-mobile-navigation__label">
                  {item.label}
                </span>
              </Link>
            );
          })}
          <button
            aria-expanded={menuOpen}
            aria-label="Mở thêm mục điều hướng"
            className="dashboard-mobile-navigation__link dashboard-mobile-navigation__more"
            onClick={(event) => {
              menuReturnFocusRef.current = event.currentTarget;
              setMenuOpen(true);
            }}
            type="button"
          >
            <IconFrame
              className="dashboard-mobile-navigation__icon"
              icon={Menu}
              size="sm"
              tone="neutral"
            />
            <span className="dashboard-mobile-navigation__label">Thêm</span>
          </button>
        </nav>
      ) : null}
      <footer className="public-footer public-footer--legal">
        <div className="public-footer__inner">
          <div className="public-footer__identity">
            <BrandMark variant="public-seal" />
            <div>
              <p className="public-footer__name">
                Trung tâm Đề cử và Xác lập Tinh Hoa Việt
              </p>
            </div>
          </div>
          <nav aria-label="Liên kết cuối trang">
            <Link href="/policies">Điều khoản sử dụng</Link>
            <Link href="/policies#privacy">Chính sách quyền riêng tư</Link>
          </nav>
        </div>
        <div className="public-footer__details">
          <div className="public-footer__organizations">
            <h2>Đơn vị đồng hành</h2>
            <div className="public-footer__partners">
              <div className="public-footer__partner">
                <Image
                  alt="Viện Những Vấn đề Phát triển (VIDS)"
                  height={72}
                  sizes="72px"
                  src="/assets/institution/logo-vids.webp"
                  width={72}
                />
                <p>
                  Viện Những Vấn đề Phát triển <span>VIDS · A-228</span>
                </p>
              </div>
              <div className="public-footer__partner">
                <Image
                  alt="Báo chí Online"
                  height={72}
                  sizes="72px"
                  src="/assets/institution/logo-baochi.webp"
                  width={72}
                />
                <p>
                  BAOCHI.ONLINE · MXH ·{" "}
                  <a
                    href="http://ankt.vn/"
                    rel="noopener noreferrer"
                    target="_blank"
                  >
                    ANKT.VN
                  </a>
                  <span>392/GP-BTTTT</span>
                </p>
              </div>
            </div>
          </div>
          <div className="public-footer__contact">
            <h2>Thông tin liên hệ</h2>
            <p>
              <MapPin aria-hidden="true" size={18} />
              <span>
                <strong>Địa chỉ</strong>181 Đề Thám, P. Bến Thành, TP. Hồ Chí
                Minh.
              </span>
            </p>
            <p>
              <MapPin aria-hidden="true" size={18} />
              <span>
                <strong>Văn phòng đại diện</strong>Lô 51, đường N1, KDC Mai
                Linh, phường Long Bình, TP. Đồng Nai.
              </span>
            </p>
            <p>
              <Phone aria-hidden="true" size={18} />
              <span>
                <strong>Ban Đề cử và Xác lập</strong>
                <a href="tel:0989553535">0989.55.3535</a>
              </span>
            </p>
            <p>
              <Mail aria-hidden="true" size={18} />
              <a href="mailto:tinhhoanoidung@gmail.com">
                tinhhoanoidung@gmail.com
              </a>
            </p>
          </div>
        </div>
        <div className="public-footer__developer">
          <h2>Đơn vị phát triển</h2>
          <DeveloperCredit showPrefix={false} />
        </div>
        <div className="public-footer__bottom">
          <p>TINH HOA VIỆT · SUY TÔN TRÍ TUỆ – LƯU TRUYỀN DI SẢN</p>
          <div
            aria-label="Mạng xã hội Tinh Hoa Việt"
            className="public-footer__social"
          >
            <a
              aria-label="Facebook Tổ chức Tinh Hoa Việt"
              href="https://www.facebook.com/profile.php?id=61582707560694"
              rel="noopener noreferrer"
              target="_blank"
            >
              <span aria-hidden="true">f</span>
            </a>
            <a
              aria-label="YouTube Tổ chức Tinh Hoa Việt"
              href="https://www.youtube.com/@tochuctinhhoaviet"
              rel="noopener noreferrer"
              target="_blank"
            >
              <span aria-hidden="true">▶</span>
            </a>
            <a
              aria-label="TikTok Tổ chức Tinh Hoa Việt"
              href="https://www.tiktok.com/@tochuctinhhoaviet"
              rel="noopener noreferrer"
              target="_blank"
            >
              <Music2 aria-hidden="true" size={19} />
            </a>
          </div>
        </div>
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
        <DeveloperCredit />
        <nav aria-label="Liên kết cuối trang">
          <Link href="/policies">Điều khoản sử dụng</Link>
          <Link href="/policies#privacy">Chính sách quyền riêng tư</Link>
        </nav>
      </footer>
    </div>
  );
}

function DeveloperCredit({ showPrefix = true }: { showPrefix?: boolean }) {
  return (
    <div className="developer-credit">
      <Image
        alt=""
        className="developer-credit__logo"
        height={48}
        sizes="48px"
        src="/assets/institution/logo-cns.png"
        width={48}
      />
      <span>
        {showPrefix ? "Phát triển bởi " : null}
        Trung tâm An ninh Công nghệ số
      </span>
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
            <div className="dashboard-workspace-drawer__account">
              <ThemeToggle />
              <LogoutButton />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
