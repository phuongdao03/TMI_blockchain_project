import type { Metadata } from "next";

import { StaffInvitationForm } from "@/components/auth/staff-invitation-form";

export const metadata: Metadata = {
  title: "Kích hoạt tài khoản nhân viên",
  description: "Xác nhận lời mời nhân viên bằng đúng tài khoản Gmail nhận thư.",
};

export default async function EmployeeInvitationPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  return <StaffInvitationForm employee token={token} />;
}
