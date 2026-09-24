import type { Metadata } from "next";

import { LoginForm } from "@/components/auth/login-form";
import type { AccountType } from "@/lib/api/types";

export const metadata: Metadata = {
  title: "Đăng nhập",
  description:
    "Đăng nhập để quản lý hồ sơ, theo dõi tiến độ hoặc tiếp tục công việc được giao.",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; accountType?: string }>;
}) {
  const { next, accountType: requestedAccountType } = await searchParams;
  const accountType: AccountType =
    requestedAccountType === "INDIVIDUAL_APPLICANT" ||
    requestedAccountType === "ORGANIZATION_APPLICANT"
      ? requestedAccountType
      : "PUBLIC_USER";
  return <LoginForm accountType={accountType} next={next} />;
}
