"use client";

import {
  BadgeCheck,
  BookOpen,
  FilePlus2,
  Bell,
  ClipboardCheck,
  House,
  LogIn,
  Menu,
  Mail,
  MapPin,
  Music2,
  Phone,
  PanelLeftClose,
  PanelLeftOpen,
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
import { VoucherSummaryBanner } from "@/components/vouchers/voucher-summary-banner";
import { DisplayNameSetupNotice } from "@/components/account/display-name-setup-notice";
import {
  CommunityRoleBadge,
  getAuthenticatedCommunityIdentity,
} from "@/components/community/community-user-identity";
import { MembershipAccountAvatar } from "@/components/membership/membership-account-avatar";
import { profileApi } from "@/lib/api/client";
import {
  isCustomerAccount,
  resolveAdminEntryPoint,
} from "@/lib/auth/role-workspaces";
import { safeLocalDestination } from "@/lib/auth/safe-destination";
import { useAuthStatus, useAuthUser } from "@/lib/auth/user-context";

import { BrandMark } from "./brand-mark";
import { DashboardContextHeader } from "./dashboard-context-header";
import { DashboardNavigation } from "./dashboard-navigation";
import { navigationGroups, activeNavigationHref } from "./navigation-config";
import { useNavigationOverlay } from "./use-navigation-overlay";
import { useNavigationAnchor } from "./use-navigation-anchor";
import { NavigationSearch } from "./navigation-search";
import { NavigationBreadcrumb } from "./navigation-breadcrumb";
import { isPreviewRelease, isPreviewRestrictedPath } from "@/lib/release-mode";
import "./navigation.css";

const publicLinks = navigationGroups.flatMap((group) => group.items);
const desktopLinks = publicLinks.filter((item) =>
  ["/", "/works", "/community", "/process", "/verify"].includes(item.href),
);

function isWorkspacePath(pathname: string) {
  return [
    "/vouchers",
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
  canSubmit,
  reviewer = false,
}: {
  pathname: string;
  personalHref: string;
  canSubmit: boolean;
  reviewer?: boolean;
}) {
  const submission = pathname === "/dossiers/new";
  const items = (
    reviewer
      ? [
          { href: "/reviews", label: "Thẩm định", icon: ClipboardCheck },
          { href: "/work-allocations", label: "Công việc", icon: BookOpen },
          { href: "/notifications", label: "Thông báo", icon: Bell },
          { href: "/account", label: "Tài khoản", icon: UserRound },
        ]
      : [
          { href: "/", label: "Trang chủ", icon: House },
          { href: "/works", label: "Khám phá", icon: BookOpen },
          ...(canSubmit && !isPreviewRelease()
            ? [{ href: "/dossiers/new", label: "Gửi hồ sơ", icon: FilePlus2 }]
            : []),
          { href: "/community", label: "Cộng đồng", icon: UsersRound },
          { href: personalHref, label: "Cá nhân", icon: UserRound },
        ]
  ).filter(
    (item) => !isPreviewRelease() || !isPreviewRestrictedPath(item.href),
  );
  const activeHref = reviewer
    ? activeNavigationHref(
        pathname,
        items.map((item) => item.href),
      )
    : undefined;
  return (
    <nav
      aria-label={reviewer ? "Điều hướng công việc" : "Điều hướng di động"}
      className="site-mobile-navigation"
      style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
    >
      {items.map(({ href, label, icon: Icon }) => {
        const active = reviewer
          ? href === activeHref
          : label === "Cá nhân"
            ? isWorkspacePath(pathname) &&
              !(submission && canSubmit && !isPreviewRelease())
            : href === "/"
              ? pathname === "/"
              : pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            aria-current={active ? "page" : undefined}
            className="site-mobile-navigation__item"
            href={href}
            key={href}
          >
            <Icon aria-hidden="true" className="site-mobile-navigation__icon" />
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function PublicShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const contextUser = useAuthUser();
  const authStatus = useAuthStatus();
  const activeUser = authStatus === "authenticated" ? contextUser : null;
  const customer = isCustomerAccount(activeUser);
  const profile = useQuery({
    queryKey: ["profile"],
    queryFn: profileApi.get,
    enabled: Boolean(activeUser),
    staleTime: 60_000,
  });
  const accountIdentity = getAuthenticatedCommunityIdentity({
    displayName: profile.data?.displayName,
    roles: activeUser?.roles,
    permissions: activeUser?.permissions,
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
  const hash = useNavigationAnchor(pathname, query);
  const headerRef = useRef<HTMLElement>(null);
  const canSubmit =
    authStatus === "unauthenticated" ||
    Boolean(activeUser?.roles.includes("USER"));
  const visibleGroups = navigationGroups.map((group) => ({
    ...group,
    label: group.label === "Khám phá" ? "Tra cứu" : group.label,
    items: group.items.filter(
      (item) =>
        (group.label !== "Khám phá" || item.href === "/verify") &&
        item.href !== "/dossiers/new",
    ),
  }));
  const activePublicHref = activeNavigationHref(
    pathname,
    publicLinks.map((item) => item.href),
    hash,
  );

  const closeMenu = (restoreFocus = true) => {
    setMenuOpen(false);
    if (restoreFocus) {
      requestAnimationFrame(() =>
        (menuReturnFocusRef.current ?? menuButtonRef.current)?.focus(),
      );
    }
  };

  const renderMobileLink = (item: (typeof publicLinks)[number]) => {
    const active = item.href === activePublicHref;
    const Icon = item.icon;
    return (
      <Link
        aria-current={active ? "page" : undefined}
        className="public-mobile-nav__link"
        key={item.href}
        href={item.href}
        onClick={() => closeMenu(false)}
      >
        <Icon aria-hidden="true" className="public-mobile-nav__icon" />
        <span>{item.label}</span>
      </Link>
    );
  };

  useNavigationOverlay(
    menuOpen,
    mobileNavigationRef,
    closeMenu,
    `${authStatus}:${activeUser?.id ?? ""}:${activeUser?.roles.join(",") ?? ""}:${activeUser?.permissions?.join(",") ?? ""}`,
  );
  useEffect(() => {
    const closeDetails = (event: Event) => {
      const target = event.target;
      headerRef.current
        ?.querySelectorAll<HTMLDetailsElement>("details[open]")
        .forEach((details) => {
          if (event instanceof KeyboardEvent && event.key === "Escape") {
            details.open = false;
            details.querySelector("summary")?.focus();
          } else if (
            event.type === "click" &&
            target instanceof Node &&
            (!details.contains(target) ||
              (target instanceof Element && target.closest("a,button")))
          )
            details.open = false;
        });
    };
    document.addEventListener("click", closeDetails);
    document.addEventListener("keydown", closeDetails);
    return () => {
      document.removeEventListener("click", closeDetails);
      document.removeEventListener("keydown", closeDetails);
    };
  }, []);
  useEffect(() => {
    headerRef.current
      ?.querySelectorAll<HTMLDetailsElement>("details[open]")
      .forEach((details) => {
        details.open = false;
      });
  }, [pathname, query, authStatus, activeUser?.id]);

  return (
    <div
      className={
        activeUser ? "public-shell public-shell--workspace" : "public-shell"
      }
    >
      <a className="skip-link" href="#main-content">
        Chuyển đến nội dung chính
      </a>
      <header className="public-header" ref={headerRef}>
        <BrandMark />
        <nav className="public-nav" aria-label="Điều hướng chính">
          {desktopLinks.map((item) => {
            const active = item.href === activePublicHref;
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
          <NavigationSearch
            identity={`${authStatus}:${activeUser?.id ?? ""}`}
          />
          <PwaInstallButton />
          <ThemeToggle />
          {activeUser ? (
            <details className="public-user-menu">
              <summary aria-label="Mở menu tài khoản">
                <MembershipAccountAvatar
                  className="public-user-menu__avatar"
                  displayName={accountIdentity.displayName}
                  size={40}
                  src={accountAvatarUrl}
                  user={activeUser}
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
                {activeUser.roles.includes("USER") && !isPreviewRelease() && (
                  <Link href="/dossiers">Hồ sơ của tôi</Link>
                )}
                {activeUser.roles.includes("MODERATOR") &&
                  !isPreviewRelease() && (
                    <Link href="/reviews">Không gian thẩm định</Link>
                  )}
                <Link href="/community/mine">Bài viết của tôi</Link>
                {!isPreviewRelease() && (
                  <Link href="/notifications">Thông báo</Link>
                )}
                {customer && <Link href="/vouchers">Voucher của tôi</Link>}
                {adminEntryPoint && !isPreviewRelease() ? (
                  <Link href={adminEntryPoint.href}>
                    {adminEntryPoint.label}
                  </Link>
                ) : null}
                <Link href="/account">Tài khoản</Link>
                {customer && <Link href="/membership">Thẻ thành viên</Link>}
                {customer && !isPreviewRelease() && (
                  <Link href="/wallet">Ví của tôi</Link>
                )}
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
            aria-label="Mở menu"
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
            role="dialog"
            aria-modal="true"
          >
            <div className="navigation-drawer-heading">
              <h2>Menu</h2>
              <button
                aria-label="Đóng menu"
                className="navigation-icon-button"
                type="button"
                onClick={() => closeMenu()}
              >
                <X aria-hidden="true" />
              </button>
            </div>
            {visibleGroups.map((group) => (
              <div
                key={group.label}
                aria-label={group.label}
                className="public-mobile-nav__section"
                role="group"
              >
                <span className="public-mobile-nav__section-label">
                  {group.label}
                </span>
                {group.items.map(renderMobileLink)}
              </div>
            ))}
            <div className="public-mobile-nav__theme">
              <span>Giao diện</span>
              <ThemeToggle />
            </div>
            {activeUser ? (
              <div className="public-mobile-nav__account-links">
                {activeUser.roles.includes("USER") && !isPreviewRelease() && (
                  <Link
                    className="public-mobile-nav__link"
                    href="/dossiers"
                    onClick={() => closeMenu(false)}
                  >
                    <BookOpen
                      aria-hidden="true"
                      className="public-mobile-nav__icon"
                    />
                    <span>Hồ sơ của tôi</span>
                  </Link>
                )}
                {activeUser.roles.includes("MODERATOR") &&
                  !isPreviewRelease() && (
                    <Link
                      className="public-mobile-nav__link"
                      href="/reviews"
                      onClick={() => closeMenu(false)}
                    >
                      <ClipboardCheck
                        aria-hidden="true"
                        className="public-mobile-nav__icon"
                      />
                      <span>Không gian thẩm định</span>
                    </Link>
                  )}
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
                </Link>
                {!isPreviewRelease() && (
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
                  </Link>
                )}
                {adminEntryPoint && !isPreviewRelease() ? (
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
      <main id="main-content">
        <NavigationBreadcrumb />
        {children}
      </main>
      <SiteMobileNavigation
        pathname={pathname}
        personalHref={activeUser ? "/workspace" : "/login?next=%2Fworkspace"}
        canSubmit={canSubmit}
      />
      <footer id="lien-he" className="public-footer public-footer--legal">
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<
    Record<string, boolean>
  >({});
  const toggleGroup = (label: string, collapsed: boolean) =>
    setCollapsedGroups((groups) => ({ ...groups, [label]: collapsed }));
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

  useNavigationOverlay(
    navigationOpen,
    navigationPanelRef,
    (restoreFocus = true) => closeNavigation({ restoreFocus }),
    `${user?.id ?? ""}:${roles.join(",")}:${user?.permissions?.join(",") ?? ""}`,
  );

  return (
    <div
      className={[
        adminArea
          ? "dashboard-shell dashboard-shell--admin"
          : "dashboard-shell dashboard-shell--workspace",
        sidebarCollapsed ? "dashboard-shell--collapsed" : "",
      ].join(" ")}
    >
      <aside className="dashboard-sidebar">
        <div className="dashboard-sidebar__header">
          <BrandMark compact />
          <button
            aria-label={
              sidebarCollapsed
                ? "Mở rộng thanh điều hướng"
                : "Thu gọn thanh điều hướng"
            }
            aria-expanded={!sidebarCollapsed}
            className="dashboard-sidebar__toggle"
            onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
            title={
              sidebarCollapsed
                ? "Mở rộng thanh điều hướng"
                : "Thu gọn thanh điều hướng"
            }
            type="button"
          >
            {sidebarCollapsed ? (
              <PanelLeftOpen aria-hidden="true" size={20} />
            ) : (
              <PanelLeftClose aria-hidden="true" size={20} />
            )}
          </button>
        </div>
        <DashboardNavigation
          collapsedGroups={collapsedGroups}
          onToggleGroup={toggleGroup}
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
        {!adminArea &&
          ["/workspace", "/dashboard"].includes(pathname) &&
          user &&
          isCustomerAccount(user) && <VoucherSummaryBanner userId={user.id} />}
        <DisplayNameSetupNotice />
        <main className="dashboard-main" id="main-content">
          <NavigationBreadcrumb />
          <div className="dashboard-page-stage" key={pathname}>
            {children}
          </div>
        </main>
      </div>
      {!adminArea ? (
        <SiteMobileNavigation
          pathname={pathname}
          personalHref="/workspace"
          canSubmit={roles.includes("USER")}
          reviewer={roles.includes("MODERATOR")}
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
              collapsedGroups={collapsedGroups}
              onToggleGroup={toggleGroup}
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
