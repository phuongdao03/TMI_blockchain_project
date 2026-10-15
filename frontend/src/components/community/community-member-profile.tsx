"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, UserRound, UserRoundCheck } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";

import { CommunityPostCard } from "@/components/community/community-post-card";
import { communityMemberApi, mediaApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import { mediaPolicies, uploadMedia } from "@/lib/media/upload";
import type {
  CommunityMemberCard,
  CommunityMemberProfile as MemberProfile,
} from "@/lib/api/types";

const PAGE_SIZE = 20;

export function CommunityMemberProfile({
  username,
  page = 1,
  view = "posts",
}: {
  username: string;
  page?: number;
  view?: "posts" | "followers" | "following";
}) {
  const user = useAuthUser();
  const viewerKey = user?.id ?? "anonymous";
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [profileError, setProfileError] = useState(false);
  const [avatarMediaId, setAvatarMediaId] = useState<string | null | undefined>(
    undefined,
  );
  const [avatarPreviewUrl, setAvatarPreviewUrl] = useState<string | null>(null);
  const [avatarUpload, setAvatarUpload] = useState({
    busy: false,
    progress: 0,
    stage: "",
    error: "",
  });
  const [draft, setDraft] = useState({
    username: "",
    displayName: "",
    bio: "",
  });
  useEffect(
    () => () => {
      if (avatarPreviewUrl?.startsWith("blob:"))
        URL.revokeObjectURL(avatarPreviewUrl);
    },
    [avatarPreviewUrl],
  );
  const profileKey = ["community", "member", username, viewerKey] as const;
  const postsKey = [
    "community",
    "member-posts",
    username,
    page,
    viewerKey,
  ] as const;
  const membersKey = [
    "community",
    "member-list",
    username,
    view,
    page,
    viewerKey,
  ] as const;
  const profile = useQuery({
    queryKey: profileKey,
    queryFn: ({ signal }) => communityMemberApi.profile(username, signal),
    staleTime: 30_000,
  });
  const posts = useQuery({
    queryKey: postsKey,
    queryFn: ({ signal }) => communityMemberApi.posts(username, page, signal),
    staleTime: 30_000,
  });
  const members = useQuery({
    queryKey: membersKey,
    queryFn: ({ signal }) =>
      view === "followers"
        ? communityMemberApi.followers(username, page, signal)
        : communityMemberApi.following(username, page, signal),
    enabled: view !== "posts",
    staleTime: 30_000,
  });
  const follow = useMutation({
    mutationFn: (member: MemberProfile) =>
      member.viewerIsFollowing
        ? communityMemberApi.unfollow(member.id)
        : communityMemberApi.follow(member.id),
    onSuccess: (result) => {
      queryClient.setQueryData<MemberProfile>(profileKey, (current) =>
        current
          ? {
              ...current,
              viewerIsFollowing: result.isFollowing,
              followerCount: result.followerCount,
            }
          : current,
      );
    },
  });
  const updateProfile = useMutation({
    mutationFn: () =>
      communityMemberApi.updateProfile({
        username: draft.username.trim(),
        displayName: draft.displayName.trim() || null,
        ...(avatarMediaId !== undefined ? { avatarMediaId } : {}),
        bio: draft.bio.trim() || null,
      }),
    onSuccess: (result) => {
      setProfileError(false);
      setEditing(false);
      setAvatarMediaId(undefined);
      setAvatarPreviewUrl(null);
      setAvatarUpload({ busy: false, progress: 0, stage: "", error: "" });
      queryClient.setQueryData(profileKey, result);
      if (result.username !== username)
        router.replace(
          `/community/members/${encodeURIComponent(result.username)}`,
        );
    },
    onError: () => setProfileError(true),
  });
  const totalPages = Math.max(
    1,
    Math.ceil(
      (posts.data?.meta.total ?? 0) / (posts.data?.meta.pageSize || PAGE_SIZE),
    ),
  );
  const memberTotalPages = Math.max(
    1,
    Math.ceil(
      (members.data?.meta.total ?? 0) /
        (members.data?.meta.pageSize || PAGE_SIZE),
    ),
  );

  if (profile.isPending) {
    return (
      <div
        aria-label="Đang tải hồ sơ thành viên"
        className="public-theme-surface min-h-[calc(100dvh-5rem)] px-4 py-12 sm:px-6"
        role="status"
      >
        <div
          aria-hidden="true"
          className="mx-auto max-w-5xl animate-pulse space-y-5"
        >
          <div className="h-28 rounded-2xl bg-[var(--theme-elevated)]" />
          <div className="h-7 w-1/3 rounded bg-[var(--theme-elevated)]" />
          <div className="h-20 rounded-xl bg-[var(--theme-elevated)]" />
        </div>
      </div>
    );
  }

  if (profile.isError || !profile.data) {
    return (
      <div className="public-theme-surface min-h-[calc(100dvh-5rem)] px-4 py-16 sm:px-6">
        <section
          className="mx-auto max-w-2xl rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-7 text-center"
          role="alert"
        >
          <h1 className="text-2xl font-bold text-[var(--theme-text)]">
            Không tìm thấy thành viên
          </h1>
          <p className="mt-3 text-sm text-[var(--theme-muted)]">
            Hồ sơ này có thể đã ngừng hoạt động hoặc không tồn tại.
          </p>
          <Link
            className="mt-5 inline-flex min-h-10 items-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)]"
            href="/community"
          >
            Về cộng đồng
          </Link>
        </section>
      </div>
    );
  }

  const member = profile.data;
  const isSelf = user?.id === member.id;
  const safeAvatarUrl = getSafeAvatarUrl(member.avatarUrl);
  const total = posts.data?.meta.total ?? member.publishedPostCount;

  function beginProfileEdit() {
    setDraft({
      username: member.username,
      displayName: member.displayName || "",
      bio: member.bio || "",
    });
    setAvatarMediaId(undefined);
    setAvatarPreviewUrl(null);
    setAvatarUpload({ busy: false, progress: 0, stage: "", error: "" });
    setProfileError(false);
    setEditing(true);
  }

  async function selectAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (!file) return;
    const previousMediaId = avatarMediaId;
    const preview = URL.createObjectURL(file);
    setAvatarPreviewUrl(preview);
    setAvatarMediaId(undefined);
    setAvatarUpload({
      busy: true,
      progress: 0,
      stage: "Đang tải ảnh lên…",
      error: "",
    });
    if (typeof previousMediaId === "string") {
      await mediaApi.deleteAsset(previousMediaId).catch(() => undefined);
    }
    try {
      const asset = await uploadMedia(file, "AVATAR", {
        onProgress: (progress) =>
          setAvatarUpload((current) => ({ ...current, progress })),
        onStage: (stage) =>
          setAvatarUpload((current) => ({
            ...current,
            stage:
              stage === "inspecting"
                ? "Đang kiểm tra ảnh an toàn…"
                : stage === "verifying"
                  ? "Đang xác nhận ảnh…"
                  : "Đang tải ảnh lên…",
          })),
      });
      setAvatarMediaId(asset.id);
      setAvatarUpload({
        busy: false,
        progress: 100,
        stage: "Ảnh đã tải lên và được xác minh.",
        error: "",
      });
    } catch (error) {
      setAvatarPreviewUrl(null);
      setAvatarUpload({
        busy: false,
        progress: 0,
        stage: "",
        error:
          error instanceof Error
            ? error.message
            : "Không thể tải ảnh. Vui lòng thử lại.",
      });
    }
  }

  async function clearAvatar() {
    if (typeof avatarMediaId === "string") {
      await mediaApi.deleteAsset(avatarMediaId).catch(() => undefined);
    }
    setAvatarMediaId(null);
    setAvatarPreviewUrl(null);
    setAvatarUpload({ busy: false, progress: 0, stage: "", error: "" });
  }

  async function cancelProfileEdit() {
    if (typeof avatarMediaId === "string") {
      await mediaApi.deleteAsset(avatarMediaId).catch(() => undefined);
    }
    setAvatarMediaId(undefined);
    setAvatarPreviewUrl(null);
    setAvatarUpload({ busy: false, progress: 0, stage: "", error: "" });
    setEditing(false);
  }

  function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateProfile.mutate();
  }

  return (
    <div className="public-theme-surface min-h-[calc(100dvh-5rem)]">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
        <Link
          className="inline-flex min-h-10 items-center text-sm font-semibold text-[var(--theme-muted)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--theme-accent)]"
          href="/community"
        >
          ← Về cộng đồng
        </Link>
        <section
          aria-labelledby="community-member-name"
          className="mt-5 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-7"
        >
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex min-w-0 items-start gap-4 sm:gap-5">
              <div
                className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-full border border-[var(--theme-border)] bg-[var(--theme-elevated)] text-lg font-bold text-[var(--theme-accent)] sm:size-20"
                aria-hidden={!safeAvatarUrl}
              >
                {safeAvatarUrl ? (
                  <Image
                    alt=""
                    className="size-full object-cover"
                    height={80}
                    src={safeAvatarUrl}
                    unoptimized
                    width={80}
                  />
                ) : (
                  getInitials(member.displayName)
                )}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold tracking-[0.18em] text-[var(--theme-accent)] uppercase">
                  Thành viên cộng đồng
                </p>
                <h1
                  id="community-member-name"
                  className="mt-2 break-words text-3xl font-bold tracking-tight text-[var(--theme-text)] sm:text-4xl"
                >
                  {member.displayName || "Thành viên"}
                </h1>
                <p className="mt-1 text-sm text-[var(--theme-muted)]">
                  @{member.username}
                </p>
                {member.bio ? (
                  <p className="mt-4 max-w-2xl whitespace-pre-wrap break-words text-sm leading-6 text-[var(--theme-text)] sm:text-base">
                    {member.bio}
                  </p>
                ) : null}
              </div>
            </div>
            {isSelf ? (
              <button
                className={followClass(false)}
                onClick={beginProfileEdit}
                type="button"
              >
                Chỉnh sửa hồ sơ
              </button>
            ) : user ? (
              <button
                aria-pressed={member.viewerIsFollowing}
                className={followClass(member.viewerIsFollowing)}
                disabled={follow.isPending}
                onClick={() => follow.mutate(member)}
                type="button"
              >
                {follow.isPending ? (
                  <LoaderCircle
                    aria-hidden="true"
                    className="size-4 animate-spin"
                  />
                ) : member.viewerIsFollowing ? (
                  <UserRoundCheck aria-hidden="true" className="size-4" />
                ) : (
                  <UserRound aria-hidden="true" className="size-4" />
                )}
                {member.viewerIsFollowing ? "Đang theo dõi" : "Theo dõi"}
              </button>
            ) : (
              <Link
                className={followClass(false)}
                href={`/login?next=${encodeURIComponent(`/community/members/${encodeURIComponent(member.username)}`)}`}
              >
                Đăng nhập để theo dõi
              </Link>
            )}
          </div>
          {follow.isError ? (
            <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
              Chưa thể cập nhật theo dõi. Vui lòng thử lại.
            </p>
          ) : null}
          {editing ? (
            <form
              aria-label="Chỉnh sửa hồ sơ cộng đồng"
              className="mt-6 grid gap-4 border-t border-[var(--theme-border)] pt-5 sm:grid-cols-2"
              onSubmit={saveProfile}
            >
              <label className="text-sm font-semibold text-[var(--theme-text)]">
                Tên người dùng
                <input
                  autoComplete="username"
                  className={profileInputClass}
                  maxLength={30}
                  minLength={3}
                  onChange={(event) =>
                    setDraft({ ...draft, username: event.target.value })
                  }
                  pattern="[A-Za-z0-9_-]{3,30}"
                  required
                  value={draft.username}
                />
              </label>
              <label className="text-sm font-semibold text-[var(--theme-text)]">
                Tên hiển thị
                <input
                  className={profileInputClass}
                  maxLength={120}
                  onChange={(event) =>
                    setDraft({ ...draft, displayName: event.target.value })
                  }
                  value={draft.displayName}
                />
              </label>
              <div className="text-sm font-semibold text-[var(--theme-text)]">
                <label htmlFor="community-avatar-upload">Ảnh đại diện</label>
                <div className="mt-2 flex flex-wrap items-center gap-4">
                  <div
                    className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-full border border-[var(--theme-border)] bg-[var(--theme-elevated)] text-sm font-bold text-[var(--theme-accent)]"
                    aria-hidden="true"
                  >
                    {avatarPreviewUrl ||
                    (avatarMediaId !== null ? safeAvatarUrl : null) ? (
                      <Image
                        alt=""
                        className="size-full object-cover"
                        height={64}
                        src={avatarPreviewUrl || safeAvatarUrl || ""}
                        unoptimized
                        width={64}
                      />
                    ) : (
                      getInitials(draft.displayName || member.displayName)
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <input
                      accept={mediaPolicies.AVATAR.accept}
                      className="block min-h-11 w-full text-sm text-[var(--theme-muted)] file:mr-3 file:min-h-10 file:rounded-lg file:border-0 file:bg-[var(--theme-accent)] file:px-4 file:font-bold file:text-[var(--theme-accent-contrast)]"
                      disabled={avatarUpload.busy || updateProfile.isPending}
                      id="community-avatar-upload"
                      onChange={selectAvatar}
                      type="file"
                    />
                    <p className="mt-1 text-xs font-normal text-[var(--theme-muted)]">
                      JPEG, PNG hoặc WebP · tối đa 5 MB
                    </p>
                    {avatarUpload.busy ? (
                      <p
                        className="mt-2 text-xs font-semibold text-[var(--theme-accent)]"
                        role="status"
                      >
                        {avatarUpload.stage}{" "}
                        {avatarUpload.progress > 0
                          ? `${avatarUpload.progress}%`
                          : ""}
                      </p>
                    ) : avatarUpload.stage ? (
                      <p
                        className="mt-2 text-xs font-semibold text-emerald-700"
                        role="status"
                      >
                        {avatarUpload.stage}
                      </p>
                    ) : null}
                    {avatarUpload.error ? (
                      <p
                        className="mt-2 text-xs font-semibold text-red-700"
                        role="alert"
                      >
                        {avatarUpload.error}
                      </p>
                    ) : null}
                    {avatarPreviewUrl ||
                    (avatarMediaId !== null && safeAvatarUrl) ? (
                      <button
                        className="mt-2 text-xs font-bold text-[var(--theme-accent)] underline underline-offset-4"
                        disabled={avatarUpload.busy || updateProfile.isPending}
                        onClick={() => void clearAvatar()}
                        type="button"
                      >
                        Xóa ảnh
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
              <label className="text-sm font-semibold text-[var(--theme-text)] sm:col-span-2">
                Giới thiệu
                <textarea
                  className={profileInputClass}
                  maxLength={500}
                  onChange={(event) =>
                    setDraft({ ...draft, bio: event.target.value })
                  }
                  rows={4}
                  value={draft.bio}
                />
              </label>
              {profileError ? (
                <p
                  className="text-sm font-semibold text-red-700 sm:col-span-2"
                  role="alert"
                >
                  Chưa thể lưu hồ sơ. Vui lòng kiểm tra tên người dùng và thử
                  lại.
                </p>
              ) : null}
              <div className="flex flex-wrap gap-2 sm:col-span-2">
                <button
                  className={followClass(false)}
                  disabled={updateProfile.isPending || avatarUpload.busy}
                  type="submit"
                >
                  {updateProfile.isPending ? (
                    <LoaderCircle
                      aria-hidden="true"
                      className="size-4 animate-spin"
                    />
                  ) : null}
                  Lưu hồ sơ
                </button>
                <button
                  className={editCancelClass}
                  disabled={avatarUpload.busy || updateProfile.isPending}
                  onClick={() => void cancelProfileEdit()}
                  type="button"
                >
                  Hủy
                </button>
              </div>
            </form>
          ) : null}
          <dl className="mt-6 grid grid-cols-2 gap-3 border-t border-[var(--theme-border)] pt-5 text-sm sm:grid-cols-4">
            <Stat label="Bài viết" value={member.publishedPostCount} />
            <StatLink
              label="Người theo dõi"
              value={member.followerCount}
              href={memberPageHref(username, 1, "followers")}
            />
            <StatLink
              label="Đang theo dõi"
              value={member.followingCount}
              href={memberPageHref(username, 1, "following")}
            />
            <div>
              <dt className="text-[var(--theme-muted)]">Tham gia</dt>
              <dd className="mt-1 font-semibold text-[var(--theme-text)]">
                {formatDate(member.joinedAt)}
              </dd>
            </div>
          </dl>
        </section>

        <nav
          aria-label="Nội dung hồ sơ"
          className="mt-8 flex gap-2 border-b border-[var(--theme-border)]"
        >
          <Link
            aria-current={view === "posts" ? "page" : undefined}
            className={profileTabClass(view === "posts")}
            href={memberPageHref(username, 1, "posts")}
          >
            Bài viết
          </Link>
          <Link
            aria-current={view === "followers" ? "page" : undefined}
            className={profileTabClass(view === "followers")}
            href={memberPageHref(username, 1, "followers")}
          >
            Người theo dõi
          </Link>
          <Link
            aria-current={view === "following" ? "page" : undefined}
            className={profileTabClass(view === "following")}
            href={memberPageHref(username, 1, "following")}
          >
            Đang theo dõi
          </Link>
        </nav>

        {view === "posts" ? (
          <section
            aria-labelledby="community-member-posts-title"
            className="mt-5"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-[var(--theme-border)] pb-4">
              <h2
                id="community-member-posts-title"
                className="text-2xl font-bold text-[var(--theme-text)]"
              >
                Bài viết đã đăng
              </h2>
              <p className="text-sm text-[var(--theme-muted)]">
                {total} bài viết
              </p>
            </div>
            {posts.isPending ? (
              <p
                className="py-7 text-sm text-[var(--theme-muted)]"
                role="status"
              >
                Đang tải bài viết…
              </p>
            ) : null}
            {posts.isError ? (
              <p
                className="py-7 text-sm font-semibold text-red-700"
                role="alert"
              >
                Chưa thể tải bài viết của thành viên này.
              </p>
            ) : null}
            {posts.data?.data.length === 0 ? (
              <p className="py-9 text-center text-sm text-[var(--theme-muted)]">
                Thành viên chưa có bài viết công khai.
              </p>
            ) : null}
            {posts.data?.data.length ? (
              <div className="divide-y divide-[var(--theme-border)]">
                {posts.data.data.map((post) => (
                  <CommunityPostCard key={post.id} post={post} />
                ))}
              </div>
            ) : null}
            {totalPages > 1 ? (
              <nav
                aria-label="Phân trang bài viết thành viên"
                className="flex items-center justify-between gap-3 border-t border-[var(--theme-border)] py-5"
              >
                {page > 1 ? (
                  <Link
                    className={paginationClass}
                    href={memberPageHref(username, page - 1)}
                  >
                    Trang trước
                  </Link>
                ) : (
                  <span aria-disabled="true" className={paginationClass}>
                    Trang trước
                  </span>
                )}
                <p
                  aria-live="polite"
                  className="text-sm text-[var(--theme-muted)]"
                >
                  Trang {page} / {totalPages}
                </p>
                {page < totalPages ? (
                  <Link
                    className={paginationClass}
                    href={memberPageHref(username, page + 1)}
                  >
                    Trang sau
                  </Link>
                ) : (
                  <span aria-disabled="true" className={paginationClass}>
                    Trang sau
                  </span>
                )}
              </nav>
            ) : null}
          </section>
        ) : (
          <section
            aria-labelledby="community-member-list-title"
            className="mt-5"
          >
            <div className="flex items-baseline justify-between gap-3 border-b border-[var(--theme-border)] pb-4">
              <h2
                className="text-2xl font-bold text-[var(--theme-text)]"
                id="community-member-list-title"
              >
                {view === "followers"
                  ? `Người theo dõi của ${member.displayName || member.username}`
                  : `${member.displayName || member.username} đang theo dõi`}
              </h2>
              <p className="text-sm text-[var(--theme-muted)]">
                {members.data?.meta.total ?? 0} thành viên
              </p>
            </div>
            {members.isPending ? (
              <p
                className="py-7 text-sm text-[var(--theme-muted)]"
                role="status"
              >
                Đang tải danh sách…
              </p>
            ) : null}
            {members.isError ? (
              <p
                className="py-7 text-sm font-semibold text-red-700"
                role="alert"
              >
                Chưa thể tải danh sách thành viên.
              </p>
            ) : null}
            {members.data?.data.length === 0 ? (
              <p className="py-9 text-center text-sm text-[var(--theme-muted)]">
                Danh sách này chưa có thành viên.
              </p>
            ) : null}
            {members.data?.data.length ? (
              <ul className="divide-y divide-[var(--theme-border)]">
                {members.data.data.map((item) => (
                  <MemberRow key={item.id} member={item} />
                ))}
              </ul>
            ) : null}
            {memberTotalPages > 1 ? (
              <nav
                aria-label="Phân trang danh sách thành viên"
                className="flex items-center justify-between gap-3 border-t border-[var(--theme-border)] py-5"
              >
                {page > 1 ? (
                  <Link
                    className={paginationClass}
                    href={memberPageHref(username, page - 1, view)}
                  >
                    Trang trước
                  </Link>
                ) : (
                  <span aria-disabled="true" className={paginationClass}>
                    Trang trước
                  </span>
                )}
                <p
                  aria-live="polite"
                  className="text-sm text-[var(--theme-muted)]"
                >
                  Trang {page} / {memberTotalPages}
                </p>
                {page < memberTotalPages ? (
                  <Link
                    className={paginationClass}
                    href={memberPageHref(username, page + 1, view)}
                  >
                    Trang sau
                  </Link>
                ) : (
                  <span aria-disabled="true" className={paginationClass}>
                    Trang sau
                  </span>
                )}
              </nav>
            ) : null}
          </section>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt className="text-[var(--theme-muted)]">{label}</dt>
      <dd className="mt-1 font-semibold text-[var(--theme-text)]">{value}</dd>
    </div>
  );
}

function StatLink({
  label,
  value,
  href,
}: {
  label: string;
  value: number;
  href: string;
}) {
  return (
    <div>
      <dt className="text-[var(--theme-muted)]">{label}</dt>
      <dd className="mt-1">
        <Link
          className="font-semibold text-[var(--theme-accent)] underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          href={href}
        >
          {label} {value}
        </Link>
      </dd>
    </div>
  );
}

function MemberRow({ member }: { member: CommunityMemberCard }) {
  const avatar = getSafeAvatarUrl(member.avatarUrl);
  return (
    <li className="flex min-w-0 items-center gap-3 py-4">
      <div
        aria-hidden={!avatar}
        className="grid size-11 shrink-0 place-items-center overflow-hidden rounded-full border border-[var(--theme-border)] bg-[var(--theme-elevated)] text-sm font-bold text-[var(--theme-accent)]"
      >
        {avatar ? (
          <Image
            alt=""
            className="size-full object-cover"
            height={44}
            src={avatar}
            unoptimized
            width={44}
          />
        ) : (
          getInitials(member.displayName || member.username)
        )}
      </div>
      <div className="min-w-0 flex-1">
        <Link
          className="block truncate font-bold text-[var(--theme-text)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          href={`/community/members/${encodeURIComponent(member.username)}`}
        >
          {member.displayName || "Thành viên"}
        </Link>
        <p className="truncate text-sm text-[var(--theme-muted)]">
          @{member.username}
        </p>
      </div>
      {member.viewerIsFollowing ? (
        <span className="shrink-0 text-xs font-semibold text-[var(--theme-muted)]">
          Đang theo dõi
        </span>
      ) : null}
    </li>
  );
}

function getSafeAvatarUrl(value: string | null): string | null {
  if (!value) return null;
  if (value.startsWith("/") && !value.startsWith("//")) return value;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? value : null;
  } catch {
    return null;
  }
}

function getInitials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(-2)
    .map((part) => part.charAt(0))
    .join("")
    .toLocaleUpperCase("vi-VN");
}

function memberPageHref(
  username: string,
  page: number,
  view: "posts" | "followers" | "following" = "posts",
): string {
  const parameters = new URLSearchParams({ page: String(page) });
  if (view !== "posts") parameters.set("view", view);
  return `/community/members/${encodeURIComponent(username)}?${parameters.toString()}`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa rõ";
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(date);
}

function followClass(active: boolean): string {
  return [
    "inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg px-4 text-sm font-bold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-60",
    active
      ? "border border-[var(--theme-border)] text-[var(--theme-text)]"
      : "bg-[var(--theme-accent)] text-[var(--theme-accent-contrast)]",
  ].join(" ");
}

const profileInputClass =
  "mt-1 min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 py-2 text-sm font-normal text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20";
const editCancelClass =
  "inline-flex min-h-11 items-center justify-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]";
const profileTabClass = (active: boolean) =>
  `inline-flex min-h-11 items-center border-b-2 px-3 text-sm font-bold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] ${active ? "border-[var(--theme-accent)] text-[var(--theme-accent)]" : "border-transparent text-[var(--theme-muted)] hover:text-[var(--theme-text)]"}`;

const paginationClass =
  "inline-flex min-h-10 items-center rounded-lg border border-[var(--theme-border)] px-3 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50";
