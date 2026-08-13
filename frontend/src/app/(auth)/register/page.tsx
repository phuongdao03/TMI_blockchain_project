import type { Metadata } from "next";

import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = {
  title: "Tạo tài khoản",
  description:
    "Chọn đúng lộ trình khám phá hoặc đề cử tài sản số. Vai trò thẩm định và Hội đồng chỉ được cấp qua bổ nhiệm nội bộ.",
};

export default function RegisterPage() {
  return <RegisterForm />;
}
