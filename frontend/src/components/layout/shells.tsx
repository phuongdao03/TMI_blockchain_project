"use client";

import {
  BadgeCheck,
  BookOpen,
  ChevronRight,
  CircleHelp,
  Download,
  Gem,
  House,
  LogIn,
  Menu,
  Mail,
  MapPin,
  Music2,
  Phone,
  Route,
  UserPlus,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { useQuery } from "@tanstack/react-query";
import { usePathname, useSearchParams } from "next/navigation";
import { type PropsWithChildren, useEffect, useRef, useState } from "react";

import { ThemeToggle } from "@/components/theme/theme-toggle";
import { PwaInstallButton } from "@/components/pwa/pwa-install-button";
import { LogoutButton } from "@/components/auth/logout-button";
import { DisplayNameSetupNotice } from "@/components/account/display-name-setup-notice";
import {
  CommunityRoleBadge,
  getAuthenticatedCommunityIdentity,
} from "@/components/community/community-user-identity";
import { UserAvatar } from "@/components/ui/user-avatar";
import { profileApi } from "@/lib/api/client";
import { resolveAdminEntryPoint } from "@/lib/auth/role-workspaces";
import { safeLocalDestination } from "@/lib/auth/safe-destination";
import { useAuthStatus, useAuthUser } from "@/lib/auth/user-context";

import { BrandMark } from "./brand-mark";
import { DashboardContextHeader } from "./dashboard-context-header";
import { DashboardNavigation } from "./dashboard-navigation";

const publicPrimaryLinks = [
  { href: "/", label: "Trang chủ", icon: House },
  { href: "/works", label: "Danh sách đề cử", icon: BookOpen },
  { href: "/community", label: "Cộng đồng", icon: UsersRound },
  { href: "/cong-dong/hoi-vien", label: "Hội viên", icon: Gem },
  { href: "/process", label: "Quy trình", icon: Route },
];
const publicUtilityLinks = [
  { href: "/verify", label: "Tra cứu bằng xác lập", icon: BadgeCheck },
  { href: "/guide", label: "Hướng dẫn", icon: CircleHelp },
];
const publicLinks = [...publicPrimaryLinks, ...publicUtilityLinks];

function isWorkspacePath(pathname: string) {
  return [
    "/workspace",
    "/dashboard",
    "/account",
    "/activity",
    "/attendance",
    "/blockchain",
    "/certificates",
    "/dossiers",
    "/help",
    "/leave",
    "/notifications",
    "/overtime",
    "/payments",
    "/wallet",
    "/membership",
    "/advertising",
    "/reviews",
    "/work-allocations",
    "/admin",
  ].some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

function SiteMobileNavigation({
  pathname,
  personalHref,
  onMore,
  moreExpanded = false,
}: {
  pathname: string;
  personalHref: string;
  onMore: (trigger: HTMLButtonElement) => void;
  moreExpanded?: boolean;
}) {
  const items = [
    { href: "/", label: "Trang chủ", icon: House },
    { href: "/works", label: "Đề cử", icon: BookOpen },
    { href: "/community", label: "Cộng đồng", icon: UsersRound },
    { href: personalHref, label: "Cá nhân", icon: UserRound },
  ];

  return (
    <nav aria-label="Điều hướng di động" className="site-mobile-navigation">
      {items.map(({ href, label, icon: Icon }) => {
        const active =
          label === "Trang chủ"
            ? pathname === "/"
            : label === "Cá nhân"
              ? isWorkspacePath(pathname)
              : pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            aria-current={active ? "page" : undefined}
            className="site-mobile-navigation__item"
            href={href}
            key={label}
          >
            <Icon aria-hidden="true" className="site-mobile-navigation__icon" />
            <span>{label}</span>
          </Link>
        );
      })}
      <button
        aria-expanded={moreExpanded}
        aria-label="Mở thêm mục điều hướng"
        className="site-mobile-navigation__item"
        onClick={(event) => onMore(event.currentTarget)}
        type="button"
      >
        <Menu aria-hidden="true" className="site-mobile-navigation__icon" />
        <span>Thêm</span>
      </button>
    </nav>
  );
}

export function PublicShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const contextUser = useAuthUser();
  const authStatus = useAuthStatus();
  const activeUser = authStatus === "authenticated" ? contextUser : null;
  const profile = useQuery({
    queryKey: ["profile"],
    queryFn: profileApi.get,
    enabled: Boolean(activeUser),
    staleTime: 60_000,
  });
  const accountIdentity = getAuthenticatedCommunityIdentity({
    displayName: profile.data?.displayName,
    roles: activeUser?.roles,
  });
  const accountAvatarUrl = profile.data?.avatarMediaId
    ? `/api/v1/community/avatars/${encodeURIComponent(profile.data.avatarMediaId)}`
    : profile.data?.avatarUrl;
  const query = searchParams.toString();
  const currentDestination = safeLocalDestination(
    `${pathname}${query ? `?${query}` : ""}`,
    "/",
  );
  const loginHref = `/login?next=${encodeURIComponent(currentDestination)}`;
  const registerHref = `/register?next=${encodeURIComponent(currentDestination)}`;
  const adminEntryPoint = activeUser
    ? resolveAdminEntryPoint(activeUser.roles, activeUser.permissions ?? [])
    : null;
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

  const renderMobileLink = (item: (typeof publicLinks)[number]) => {
    const active =
      item.href === "/"
        ? pathname === item.href
        : pathname === item.href || pathname.startsWith(`${item.href}/`);
    const Icon = item.icon;
    return (
      <Link
        aria-current={active ? "page" : undefined}
        className="public-mobile-nav__link"
        key={item.href}
        ref={item.href === "/" ? firstMobileLinkRef : undefined}
        href={item.href}
        onClick={() => closeMenu(false)}
      >
        <Icon aria-hidden="true" className="public-mobile-nav__icon" />
        <span>{item.label}</span>
        <ChevronRight
          aria-hidden="true"
          className="public-mobile-nav__chevron"
        />
      </Link>
    );
  };

  useEffect(() => {
    if (!menuOpen) return;

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

    document.addEventListener("keydown", handleDrawerKeyboard);
    firstMobileLinkRef.current?.focus();

    return () => {
      document.removeEventListener("keydown", handleDrawerKeyboard);
    };
  }, [menuOpen]);

  return (
    <div
      className={
        activeUser ? "public-shell public-shell--workspace" : "public-shell"
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
          {activeUser ? (
            <details className="public-user-menu">
              <summary aria-label="Mở menu tài khoản">
                <UserAvatar
                  className="public-user-menu__avatar"
                  displayName={accountIdentity.displayName}
                  size={32}
                  src={accountAvatarUrl}
                />
                <span className="public-user-menu__identity">
                  <span className="public-user-menu__display-name">
                    {accountIdentity.displayName}
                  </span>
                  <CommunityRoleBadge
                    isAdmin={accountIdentity.isAdmin}
                    roleLabel={accountIdentity.roleLabel}
                  />
                </span>
              </summary>
              <nav
                aria-label="Menu tài khoản"
                className="public-user-menu__panel"
              >
                <Link href="/workspace">Không gian cá nhân</Link>
                <Link href="/community/mine">Bài viết của tôi</Link>
                <Link href="/notifications">Thông báo</Link>
                {adminEntryPoint ? (
                  <Link href={adminEntryPoint.href}>
                    {adminEntryPoint.label}
                  </Link>
                ) : null}
                <Link href="/account">Tài khoản</Link>
                <Link href="/membership">Thẻ thành viên</Link>
                <Link href="/wallet">Ví của tôi</Link>
                <LogoutButton />
              </nav>
            </details>
          ) : authStatus === "unauthenticated" ? (
            <>
              <Link
                className="public-header__auth-link public-header__login"
                href={loginHref}
              >
                <LogIn aria-hidden="true" />
                <span>Đăng nhập</span>
              </Link>
              <Link
                className="public-header__auth-link public-header__register"
                href={registerHref}
              >
                <UserPlus aria-hidden="true" />
                <span>Đăng ký</span>
              </Link>
            </>
          ) : (
            <span className="public-header__session-status" role="status">
              {authStatus === "loading"
                ? "Đang xác minh tài khoản"
                : "Không thể xác minh phiên"}
            </span>
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
      {menuOpen ? (
        <div className="public-mobile-drawer">
          <button
            type="button"
            className="public-mobile-drawer__backdrop"
            aria-hidden="true"
            tabIndex={-1}
            onClick={() => closeMenu()}
          />
          <nav
            ref={mobileNavigationRef}
            id="public-mobile-navigation"
            className="public-mobile-nav"
            aria-label="Menu công khai"
          >
            <div
              aria-label="Khám phá"
              className="public-mobile-nav__section"
              role="group"
            >
              <span className="public-mobile-nav__section-label">Khám phá</span>
              {publicPrimaryLinks.map(renderMobileLink)}
            </div>
            <div
              aria-label="Tiện ích"
              className="public-mobile-nav__section public-mobile-nav__section--secondary"
              role="group"
            >
              <span className="public-mobile-nav__section-label">Tiện ích</span>
              {publicUtilityLinks.map(renderMobileLink)}
              <Link
                aria-current={pathname === "/install" ? "page" : undefined}
                className="public-mobile-nav__link"
                href="/install"
                onClick={() => closeMenu(false)}
              >
                <Download
                  aria-hidden="true"
                  className="public-mobile-nav__icon"
                />
                <span>Cài ứng dụng</span>
                <ChevronRight
                  aria-hidden="true"
                  className="public-mobile-nav__chevron"
                />
              </Link>
            </div>
            <div className="public-mobile-nav__theme">
              <span>Giao diện</span>
              <ThemeToggle />
            </div>
            {activeUser ? (
              <div className="public-mobile-nav__account-links">
                <Link
                  className="public-mobile-nav__link"
                  href="/workspace"
                  onClick={() => closeMenu(false)}
                >
                  <UserRound
                    aria-hidden="true"
                    className="public-mobile-nav__icon"
                  />
                  <span>Không gian cá nhân</span>
                  <ChevronRight
                    aria-hidden="true"
                    className="public-mobile-nav__chevron"
                  />
                </Link>
                <Link
                  className="public-mobile-nav__link"
                  href="/community/mine"
                  onClick={() => closeMenu(false)}
                >
                  <UsersRound
                    aria-hidden="true"
                    className="public-mobile-nav__icon"
                  />
                  <span>Bài viết của tôi</span>
                  <ChevronRight
                    aria-hidden="true"
                    className="public-mobile-nav__chevron"
                  />
                </Link>
                <Link
                  className="public-mobile-nav__link"
                  href="/notifications"
                  onClick={() => closeMenu(false)}
                >
                  <Mail
                    aria-hidden="true"
                    className="public-mobile-nav__icon"
                  />
                  <span>Thông báo</span>
                  <ChevronRight
                    aria-hidden="true"
                    className="public-mobile-nav__chevron"
                  />
                </Link>
                {adminEntryPoint ? (
                  <Link
                    className="public-mobile-nav__link"
                    href={adminEntryPoint.href}
                    onClick={() => closeMenu(false)}
                  >
                    <BadgeCheck
                      aria-hidden="true"
                      className="public-mobile-nav__icon"
                    />
                    <span>{adminEntryPoint.label}</span>
                    <ChevronRight
                      aria-hidden="true"
                      className="public-mobile-nav__chevron"
                    />
                  </Link>
                ) : null}
                <Link
                  className="public-mobile-nav__link"
                  href="/account"
                  onClick={() => closeMenu(false)}
                >
                  <UserRound
                    aria-hidden="true"
                    className="public-mobile-nav__icon"
                  />
                  <span>Tài khoản</span>
                  <ChevronRight
                    aria-hidden="true"
                    className="public-mobile-nav__chevron"
                  />
                </Link>
                <LogoutButton />
              </div>
            ) : authStatus === "unauthenticated" ? (
              <div
                aria-label="Tài khoản"
                className="public-mobile-nav__account"
                role="group"
              >
                <Link
                  className="public-mobile-nav__login"
                  href={loginHref}
                  onClick={() => closeMenu(false)}
                >
                  <LogIn aria-hidden="true" />
                  <span>Đăng nhập</span>
                </Link>
                <Link
                  className="public-mobile-nav__register"
                  href={registerHref}
                  onClick={() => closeMenu(false)}
                >
                  <UserPlus aria-hidden="true" />
                  <span>Đăng ký</span>
                </Link>
              </div>
            ) : (
              <p className="public-mobile-nav__session-status" role="status">
                {authStatus === "loading"
                  ? "Đang xác minh tài khoản"
                  : "Không thể xác minh phiên"}
              </p>
            )}
          </nav>
        </div>
      ) : null}
      <DisplayNameSetupNotice />
      <main id="main-content">{children}</main>
      <SiteMobileNavigation
        pathname={pathname}
        personalHref={activeUser ? "/workspace" : loginHref}
        moreExpanded={menuOpen}
        onMore={(trigger) => {
          menuReturnFocusRef.current = trigger;
          setMenuOpen(true);
        }}
      />
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
                <a href="tel:0834112288">0834.11.22.88</a>
                <a href="tel:0989553535">0989.55.3535</a>
              </span>
            </p>
            <p>
              <Mail aria-hidden="true" size={18} />
              <a href="mailto:decu@tinhhoaviet.org.vn">
                decu@tinhhoaviet.org.vn
              </a>
            </p>
          </div>
        </div>
        <div className="public-footer__developer">
          <h2>Đơn vị phát triển</h2>
          <div className="developer-credit">
            <Image
              alt="Biểu trưng Trung tâm An ninh Công nghệ số"
              className="developer-credit__logo"
              height={40}
              src="/assets/institution/logo-cns.png"
              width={40}
            />
            <strong>Trung tâm An ninh Công nghệ số - CNS</strong>
          </div>
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
        <nav aria-label="Liên kết cuối trang">
          <Link href="/policies">Điều khoản sử dụng</Link>
          <Link href="/policies#privacy">Chính sách quyền riêng tư</Link>
        </nav>
        <span className="developer-credit">
          Đơn vị phát triển · Trung tâm An ninh Công nghệ số - CNS
        </span>
      </footer>
    </div>
  );
}

export function DashboardShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const adminArea = pathname.startsWith("/admin");
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
    <div
      className={
        adminArea
          ? "dashboard-shell dashboard-shell--admin"
          : "dashboard-shell dashboard-shell--workspace"
      }
    >
      <aside className="dashboard-sidebar">
        <BrandMark compact />
        <DashboardNavigation
          area={adminArea ? "admin" : "workspace"}
          roles={roles}
          showQuickNavigation={false}
        />
      </aside>
      <div className="dashboard-shell__content">
        <DashboardContextHeader
          navigationButtonRef={navigationButtonRef}
          navigationOpen={navigationOpen}
          onOpenNavigation={() => openNavigation(navigationButtonRef.current)}
          user={user}
        />
        <DisplayNameSetupNotice />
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
        showQuickNavigation={false}
      />
      {!adminArea ? (
        <SiteMobileNavigation
          pathname={pathname}
          personalHref="/workspace"
          onMore={(trigger) => openNavigation(trigger)}
          moreExpanded={navigationOpen}
        />
      ) : null}
      {navigationOpen ? (
        <div className="dashboard-workspace-drawer">
          <button
            aria-label={`Đóng điều hướng ${adminArea ? "quản trị" : "workspace"}`}
            className="dashboard-workspace-drawer__backdrop"
            onClick={() => closeNavigation()}
            type="button"
          />
          <div
            aria-label={
              adminArea ? "Điều hướng quản trị" : "Điều hướng workspace"
            }
            aria-modal="true"
            className="dashboard-workspace-drawer__panel"
            id="dashboard-workspace-navigation"
            ref={navigationPanelRef}
            role="dialog"
          >
            <div className="dashboard-workspace-drawer__header">
              <div>
                <p>Đề cử Tinh Hoa Việt</p>
                <h2>{adminArea ? "Khu vực quản trị" : "Không gian cá nhân"}</h2>
              </div>
              <button
                aria-label={`Đóng điều hướng ${adminArea ? "quản trị" : "workspace"}`}
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
              area={adminArea ? "admin" : "workspace"}
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
