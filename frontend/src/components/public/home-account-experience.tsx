"use client";

import { ArrowRight, ShieldCheck, UserRound } from "lucide-react";
import Link from "next/link";

import { resolveDefaultWorkspace } from "@/lib/auth/role-workspaces";
import { useAuthStatus, useAuthUser } from "@/lib/auth/user-context";

export function HomeHeroAccountMessage() {
  const authStatus = useAuthStatus();
  const user = useAuthUser();
  const message =
    authStatus === "unauthenticated"
      ? "Tạo tài khoản để gửi hồ sơ và theo dõi hành trình xác lập."
      : authStatus === "authenticated" && user
        ? "Theo dõi hồ sơ, phản hồi và thông tin của bạn trong không gian cá nhân."
        : "Đang xác minh phiên đăng nhập.";

  return (
    <p className="registry-hero__copy--compact mt-5 max-w-[41rem] text-[0.95rem] leading-7 text-slate-300 sm:mt-8 sm:text-lg sm:leading-8">
      {message}
    </p>
  );
}

export function HomeHeroAccountActions() {
  const authStatus = useAuthStatus();
  const user = useAuthUser();

  if (authStatus === "authenticated" && user) {
    return (
      <nav
        aria-label="Không gian cá nhân"
        className="registry-hero__buttons mt-9 flex flex-col gap-3 sm:flex-row"
      >
        <Link
          className="registry-button registry-button-primary"
          href={resolveDefaultWorkspace(user.roles, user.permissions ?? [])}
        >
          Không gian cá nhân
          <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </nav>
    );
  }

  if (authStatus !== "unauthenticated") return null;

  return (
    <nav
      aria-label="Truy cập tài khoản"
      className="registry-hero__buttons mt-9 flex flex-col gap-3 sm:flex-row"
    >
      <Link
        className="registry-button registry-button-primary"
        href="/register"
      >
        Đăng ký
      </Link>
      <Link
        className="registry-button registry-button-auth-secondary"
        href="/login"
      >
        Đăng nhập
      </Link>
    </nav>
  );
}

export function HomeClosingAccountCta({ preview }: { preview: boolean }) {
  const authStatus = useAuthStatus();
  const user = useAuthUser();

  if (authStatus === "authenticated" && user) {
    return (
      <section className="home-cta border-t">
        <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-16 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div className="max-w-2xl">
            <ShieldCheck
              aria-hidden="true"
              className="home-cta__icon size-6 text-primary-700"
            />
            <h2 className="mt-5 text-3xl font-semibold tracking-tight">
              Tiếp tục hành trình Tinh Hoa Việt
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Theo dõi hồ sơ, phản hồi và các cập nhật trong không gian cá nhân.
            </p>
          </div>
          <Link
            className="registry-button registry-button-primary"
            href={resolveDefaultWorkspace(user.roles, user.permissions ?? [])}
          >
            Không gian cá nhân
            <UserRound aria-hidden="true" className="size-4" />
          </Link>
        </div>
      </section>
    );
  }

  if (authStatus !== "unauthenticated") return null;

  return (
    <section className="home-cta border-t">
      <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-16 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <div className="max-w-2xl">
          <ShieldCheck
            aria-hidden="true"
            className="home-cta__icon size-6 text-primary-700"
          />
          <h2 className="mt-5 text-3xl font-semibold tracking-tight">
            {preview
              ? "Muốn theo dõi hành trình Tinh Hoa Việt?"
              : "Tiếp tục khám phá Tinh Hoa Việt"}
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            {preview
              ? "Tạo tài khoản để lưu nội dung quan tâm và theo dõi các cập nhật chính thức của chương trình."
              : "Tạo tài khoản để gửi hồ sơ, nhận phản hồi và quản lý thông tin của bạn."}
          </p>
        </div>
        <Link
          className="registry-button registry-button-primary"
          href="/register"
        >
          Tạo tài khoản <UserRound aria-hidden="true" className="size-4" />
        </Link>
      </div>
    </section>
  );
}
