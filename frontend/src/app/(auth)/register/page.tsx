import type { Metadata } from "next";

import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = {
  title: "Tạo tài khoản",
  description:
    "Tạo tài khoản Đề cử Tinh Hoa Việt để sử dụng các tiện ích cá nhân.",
};

export default function RegisterPage() {
  return <RegisterForm />;
}
