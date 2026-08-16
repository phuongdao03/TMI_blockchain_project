import type { Metadata } from "next";

import { StaffInvitationForm } from "@/components/auth/staff-invitation-form";

export const metadata: Metadata = {
  title: "Xác nhận lời mời",
  description:
    "Xác nhận lời mời tham gia đội ngũ vận hành Đề cử Tinh Hoa Việt.",
};

export default async function StaffInvitationPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  return <StaffInvitationForm token={token} />;
}
