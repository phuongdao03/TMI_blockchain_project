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
      <header className="rounded-3xl border border-neutral-200 bg-white px-6 py-7 sm:px-8">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-600">
          Thông tin tài khoản
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl">
          Tài khoản của bạn
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-700">
          Xem thông tin cá nhân, cập nhật cách liên hệ và quản lý tổ chức của
          bạn.
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
              ? "Thông tin cá nhân của bạn. Nếu có hồ sơ nhân viên, thông tin công việc được đồng bộ từ quản trị nhân sự."
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
