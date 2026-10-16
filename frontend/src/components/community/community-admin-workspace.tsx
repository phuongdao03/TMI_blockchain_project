"use client";

import { useState } from "react";

import {
  CommunityCategoryManagement,
  CommunityModerationHistoryPanel,
  CommunityReportQueue,
} from "@/components/community/community-admin-panels";
import {
  CommunityAdminCommentsWorkspace,
  CommunityAdminMembersWorkspace,
  CommunityAdminPostsWorkspace,
} from "@/components/community/community-admin-content-workspaces";
import { useAuthUser } from "@/lib/auth/user-context";

type WorkspaceView =
  | "posts"
  | "comments"
  | "members"
  | "reports"
  | "history"
  | "categories";

export function CommunityAdminWorkspace() {
  const user = useAuthUser();
  const isSuperAdmin = user?.roles.includes("SUPER_ADMIN") ?? false;
  const canModerate =
    isSuperAdmin ||
    (user?.permissions?.includes("community.moderate") ?? false);
  const canManage =
    isSuperAdmin || (user?.permissions?.includes("community.manage") ?? false);
  const views: { id: WorkspaceView; label: string }[] = [
    ...(canModerate
      ? [
          { id: "posts" as const, label: "Bài viết" },
          { id: "comments" as const, label: "Bình luận" },
          { id: "members" as const, label: "Thành viên" },
          { id: "reports" as const, label: "Báo cáo" },
          { id: "history" as const, label: "Lịch sử" },
        ]
      : []),
    ...(canManage
      ? [{ id: "categories" as const, label: "Danh mục" }]
      : []),
  ];
  const [selectedView, setSelectedView] = useState<WorkspaceView>(
    canModerate ? "posts" : "categories",
  );

  if (views.length === 0) return null;

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
      <header className="mb-6 border-b border-[var(--theme-border)] pb-5">
        <p className="text-xs font-bold tracking-[0.16em] text-[var(--theme-accent)] uppercase">
          Không gian quản trị
        </p>
        <h1 className="mt-2 text-3xl font-bold text-[var(--theme-text)]">
          Cộng đồng
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
          Xem xét nội dung và quản lý các thiết lập cộng đồng theo quyền được
          cấp.
        </p>
      </header>

      <div
        aria-label="Công cụ quản trị cộng đồng"
        className="mb-6 flex flex-wrap gap-2"
        role="group"
      >
        {views.map((view) => (
          <button
            aria-pressed={selectedView === view.id}
            className={`min-h-11 rounded-full border px-4 text-sm font-bold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] ${selectedView === view.id ? "border-[var(--theme-accent)] bg-[var(--theme-accent)] text-[var(--theme-accent-contrast)]" : "border-[var(--theme-border)] bg-[var(--theme-surface)] text-[var(--theme-text)] hover:border-[var(--theme-accent)]"}`}
            key={view.id}
            onClick={() => setSelectedView(view.id)}
            type="button"
          >
            {view.label}
          </button>
        ))}
      </div>

      <div aria-live="polite" className="min-w-0">
        {selectedView === "posts" && canModerate ? (
          <CommunityAdminPostsWorkspace />
        ) : null}
        {selectedView === "comments" && canModerate ? (
          <CommunityAdminCommentsWorkspace />
        ) : null}
        {selectedView === "members" && canModerate ? (
          <CommunityAdminMembersWorkspace />
        ) : null}
        {selectedView === "reports" && canModerate ? (
          <CommunityReportQueue />
        ) : null}
        {selectedView === "history" && canModerate ? (
          <CommunityModerationHistoryPanel />
        ) : null}
        {selectedView === "categories" && canManage ? (
          <CommunityCategoryManagement />
        ) : null}
      </div>
    </main>
  );
}
