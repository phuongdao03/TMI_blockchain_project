"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, CircleAlert, UserRound } from "lucide-react";
import { useState } from "react";

import { OrganizationPanel } from "@/components/account/organization-panel";
import { ProfileForm } from "@/components/account/profile-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError, organizationApi, profileApi } from "@/lib/api/client";
import type { ProfileUpdate } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type AccountTab = "profile" | "organization";

export function AccountSettings() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<AccountTab>("profile");
  const profileQuery = useQuery({
    queryKey: ["profile"],
    queryFn: profileApi.get,
  });
  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: () => organizationApi.list(),
  });
  const profileMutation = useMutation({
    mutationFn: (profile: ProfileUpdate) => profileApi.update(profile),
    onSuccess: (profile) => {
      queryClient.setQueryData(["profile"], profile);
    },
  });
  const avatarMutation = useMutation({
    mutationFn: (mediaId: string) =>
      profileApi.updateAvatar({ avatarMediaId: mediaId }),
    onSuccess: (profile) => {
      queryClient.setQueryData(["profile"], profile);
    },
  });

  const queryError =
    profileQuery.error ??
    organizationsQuery.error ??
    profileMutation.error ??
    avatarMutation.error;

  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <header className="rounded-3xl bg-ink-950 px-6 py-7 text-white shadow-xl shadow-slate-950/10 sm:px-8">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-gold-300">
          Không gian tin cậy
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          Tài khoản &amp; tổ chức
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
          Quản lý danh tính, thông tin pháp lý và quyền truy cập của đội ngũ
          trong một khu vực bảo mật.
        </p>
      </header>

      <div
        aria-label="Cài đặt tài khoản"
        className="inline-flex rounded-2xl border border-neutral-200 bg-white p-1 shadow-sm"
        role="tablist"
      >
        {[
          { id: "profile" as const, label: "Hồ sơ cá nhân", icon: UserRound },
          { id: "organization" as const, label: "Tổ chức", icon: Building2 },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <button
              aria-selected={tab === item.id}
              className={cn(
                "inline-flex min-h-11 items-center gap-2 rounded-xl px-4 text-sm font-semibold transition-colors",
                tab === item.id
                  ? "bg-primary-600 text-white shadow-md shadow-primary-950/15"
                  : "text-neutral-600 hover:bg-neutral-50",
              )}
              key={item.id}
              onClick={() => setTab(item.id)}
              role="tab"
              type="button"
            >
              <Icon aria-hidden="true" className="size-4" />
              {item.label}
            </button>
          );
        })}
      </div>

      {queryError ? (
        <p
          className="flex items-center gap-2 rounded-2xl border border-error bg-primary-50 p-4 text-sm font-medium text-error"
          role="alert"
        >
          <CircleAlert aria-hidden="true" className="size-5" />
          {queryError instanceof ApiError
            ? queryError.message
            : "Không thể tải dữ liệu tài khoản. Vui lòng thử lại."}
        </p>
      ) : null}

      <Card className="shadow-none">
        <CardHeader className="border-b border-neutral-100">
          <CardTitle>
            {tab === "profile" ? "Thông tin cá nhân" : "Quản trị tổ chức"}
          </CardTitle>
          <CardDescription>
            {tab === "profile"
              ? "Thông tin này được dùng xuyên suốt hồ sơ xác minh."
              : "Quản lý thông tin tổ chức và thành viên theo đúng vai trò."}
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          {tab === "profile" ? (
            profileQuery.isPending ? (
              <p className="py-12 text-center text-sm text-neutral-500">
                Đang tải hồ sơ…
              </p>
            ) : profileQuery.data ? (
              <ProfileForm
                avatarLinkPending={avatarMutation.isPending}
                onAvatarUploaded={(mediaId) => avatarMutation.mutate(mediaId)}
                onSave={async (profile) => {
                  await profileMutation.mutateAsync(profile);
                }}
                profile={profileQuery.data}
              />
            ) : null
          ) : organizationsQuery.isPending ? (
            <p className="py-12 text-center text-sm text-neutral-500">
              Đang tải tổ chức…
            </p>
          ) : organizationsQuery.data ? (
            <OrganizationPanel organizations={organizationsQuery.data.data} />
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
