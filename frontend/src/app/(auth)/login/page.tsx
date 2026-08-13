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
  const accountType: AccountType = [
    "PUBLIC_USER",
    "INDIVIDUAL_APPLICANT",
    "ORGANIZATION_APPLICANT",
  ].includes(requestedAccountType ?? "")
    ? (requestedAccountType as AccountType)
    : "PUBLIC_USER";
  return <LoginForm accountType={accountType} next={next} />;
}
