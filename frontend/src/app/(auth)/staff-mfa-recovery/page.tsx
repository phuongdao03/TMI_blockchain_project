import type { Metadata } from "next";

import { StaffMfaRecoveryForm } from "@/components/auth/staff-mfa-recovery-form";

export const metadata: Metadata = {
  title: "Khôi phục bảo vệ tài khoản",
  description: "Thiết lập lại ứng dụng xác thực cho tài khoản nhân sự TMI.",
};

export default function StaffMfaRecoveryPage() {
  return <StaffMfaRecoveryForm />;
}
