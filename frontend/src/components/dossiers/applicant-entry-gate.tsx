"use client";

import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { RoleGate } from "@/components/auth/role-gate";
import { ApplicantUpgradeCard } from "@/components/dashboard/applicant-upgrade-card";
import { useAuthUser } from "@/lib/auth/user-context";

export function ApplicantEntryGate({ children }: { children: ReactNode }) {
  const user = useAuthUser();
  const client = useQueryClient();
  if (
    user?.accountType === "PUBLIC_USER" &&
    user.roles.every((role) => role === "VIEWER")
  ) {
    return (
      <div className="mx-auto max-w-3xl space-y-5">
        <header>
          <h1 className="text-2xl font-bold">Trước khi bắt đầu hồ sơ</h1>
          <p className="mt-2 text-sm text-[var(--theme-muted)]">
            Chọn tư cách gửi để sử dụng đúng biểu mẫu. Đây là bước thiết lập một
            lần.
          </p>
        </header>
        <ApplicantUpgradeCard
          startChoosing
          onUpgraded={(upgraded) =>
            client.setQueryData(["auth", "me"], upgraded)
          }
        />
      </div>
    );
  }
  return <RoleGate allowed={["USER"]}>{children}</RoleGate>;
}
