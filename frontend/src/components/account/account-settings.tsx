"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, CircleAlert, LoaderCircle, UserRound } from "lucide-react";
import { useState } from "react";

import { OrganizationPanel } from "@/components/account/organization-panel";
import { ProfileForm } from "@/components/account/profile-form";
import { WorkspacePageHeader } from "@/components/layout/workspace-page-header";
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
    enabled: tab === "organization",
  });
  const profileMutation = useMutation({
    mutationFn: (profile: ProfileUpdate) => profileApi.update(profile),
    onSuccess: (profile) => {
      queryClient.setQueryData(["profile"], profile);
      void queryClient.invalidateQueries({ queryKey: ["community"] });
    },
  });
  const avatarMutation = useMutation({
    mutationFn: (mediaId: string) =>
      profileApi.updateAvatar({ avatarMediaId: mediaId }),
    onSuccess: (profile) => {
      queryClient.setQueryData(["profile"], profile);
      void queryClient.invalidateQueries({ queryKey: ["community"] });
    },
  });

  const queryError =
    (tab === "profile" ? profileQuery.error : null) ??
    (tab === "organization" ? organizationsQuery.error : null) ??
    profileMutation.error ??
    avatarMutation.error;

  return (
    <div className="workspace-screen mx-auto max-w-7xl space-y-6 pb-12">
      <WorkspacePageHeader
        description="Xem thông tin cá nhân, cập nhật cách liên hệ và quản lý tổ chức của bạn."
        icon={UserRound}
        section="Cài đặt"
        title="Tài khoản của bạn"
      />

      <div className="grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <nav
          aria-label="Cài đặt tài khoản"
          className="flex gap-2 overflow-x-auto border-b border-[var(--theme-border)] pb-2 lg:flex-col lg:overflow-visible lg:border-b-0 lg:border-r lg:pb-0 lg:pr-5"
          role="tablist"
        >
          {[
            { id: "profile" as const, label: "Hồ sơ cá nhân", icon: UserRound },
            { id: "organization" as const, label: "Tổ chức", icon: Building2 },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <button
                aria-controls="account-settings-panel"
                aria-selected={tab === item.id}
                className={cn(
                  "inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg px-3 text-left text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] lg:w-full",
                  tab === item.id
                    ? "bg-[var(--theme-accent)] text-[var(--theme-accent-contrast)]"
                    : "text-[var(--theme-muted)] hover:bg-[var(--theme-elevated)] hover:text-[var(--theme-text)]",
                )}
                id={`account-${item.id}-tab`}
                key={item.id}
                onClick={() => setTab(item.id)}
                onKeyDown={(event) => {
                  if (
                    event.key !== "ArrowRight" &&
                    event.key !== "ArrowLeft" &&
                    event.key !== "ArrowDown" &&
                    event.key !== "ArrowUp"
                  ) {
                    return;
                  }
                  event.preventDefault();
                  const nextTab =
                    item.id === "profile" ? "organization" : "profile";
                  setTab(nextTab);
                  document.getElementById(`account-${nextTab}-tab`)?.focus();
                }}
                role="tab"
                tabIndex={tab === item.id ? 0 : -1}
                type="button"
              >
                <Icon aria-hidden="true" className="size-4" />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="min-w-0 space-y-4">
          {queryError ? (
            <p
              className="flex items-center gap-2 rounded-xl border border-error bg-primary-50 p-4 text-sm font-medium text-error"
              role="alert"
            >
              <CircleAlert aria-hidden="true" className="size-5" />
              {queryError instanceof ApiError
                ? queryError.message
                : "Không thể tải dữ liệu tài khoản. Vui lòng thử lại."}
            </p>
          ) : null}

          <div
            aria-labelledby={`account-${tab}-tab`}
            className="min-w-0"
            id="account-settings-panel"
            role="tabpanel"
            tabIndex={0}
          >
            <Card className="shadow-none">
              <CardHeader className="border-b border-neutral-100">
                <CardTitle>
                  {tab === "profile"
                    ? "Hồ sơ cá nhân và nhân viên"
                    : "Quản trị tổ chức"}
                </CardTitle>
                <CardDescription>
                  {tab === "profile"
                    ? "Tự cập nhật họ tên, số điện thoại và ảnh đại diện. Thông tin công việc do quản trị nhân sự quản lý."
                    : "Quản lý thông tin tổ chức và thành viên theo đúng vai trò."}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                {tab === "profile" ? (
                  profileQuery.isPending ? (
                    <p
                      className="flex min-h-40 items-center justify-center gap-3 text-sm text-neutral-500"
                      role="status"
                    >
                      <LoaderCircle
                        aria-hidden="true"
                        className="size-5 animate-spin"
                      />
                      Đang tải hồ sơ…
                    </p>
                  ) : profileQuery.data ? (
                    <ProfileForm
                      avatarLinkPending={avatarMutation.isPending}
                      onAvatarUploaded={(mediaId) =>
                        avatarMutation.mutate(mediaId)
                      }
                      onSave={async (profile) => {
                        await profileMutation.mutateAsync(profile);
                      }}
                      profile={profileQuery.data}
                    />
                  ) : (
                    <div className="py-8 text-center">
                      <p className="text-sm text-[var(--theme-muted)]">
                        Chưa thể tải hồ sơ cá nhân.
                      </p>
                      <button
                        className="mt-3 min-h-11 rounded-xl border border-[var(--theme-border)] px-4 text-sm font-bold"
                        onClick={() => void profileQuery.refetch()}
                        type="button"
                      >
                        Thử tải lại
                      </button>
                    </div>
                  )
                ) : organizationsQuery.isPending ? (
                  <p className="py-12 text-center text-sm text-neutral-500">
                    Đang tải tổ chức…
                  </p>
                ) : organizationsQuery.data ? (
                  <OrganizationPanel
                    organizations={organizationsQuery.data.data}
                  />
                ) : null}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
