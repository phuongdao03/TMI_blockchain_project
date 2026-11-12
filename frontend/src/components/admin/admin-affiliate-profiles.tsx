"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { adminAffiliateApi } from "@/lib/api/client";
import type {
  AdminAffiliateCommission,
  AdminAffiliateProfile,
  AffiliateProfileStatusChange,
  AffiliateReferral,
} from "@/lib/api/types";
import {
  affiliateServiceLabel,
  commissionStatusLabel,
  profileStatusLabel,
} from "@/lib/affiliate-presentation";
import { formatVnd } from "@/lib/wallet/summary";

const inputClass =
  "min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm";

function ProfileReferralRow({ item }: { item: AffiliateReferral }) {
  return (
    <li className="grid gap-2 border-b border-[var(--theme-border)] py-3 last:border-b-0 sm:grid-cols-[1fr_auto] sm:items-center">
      <div>
        <p className="font-semibold">Lượt giới thiệu</p>
        <p className="text-xs text-[var(--theme-muted)]">
          Ghi nhận {new Date(item.attributedAt).toLocaleDateString("vi-VN")} ·
          hết hạn {new Date(item.expiresAt).toLocaleDateString("vi-VN")}
        </p>
      </div>
      <div className="grid grid-cols-3 gap-3 text-sm sm:text-right">
        <p>
          <span className="block text-xs text-[var(--theme-muted)]">
            Lượt chuyển đổi
          </span>
          <strong>{item.conversionCount}</strong>
        </p>
        <p>
          <span className="block text-xs text-[var(--theme-muted)]">
            Doanh thu
          </span>
          <strong>{formatVnd(item.revenueMinor)}</strong>
        </p>
        <p>
          <span className="block text-xs text-[var(--theme-muted)]">
            Hoa hồng
          </span>
          <strong>{formatVnd(item.commissionAmountMinor)}</strong>
        </p>
      </div>
    </li>
  );
}

function ProfileCommissionRow({ item }: { item: AdminAffiliateCommission }) {
  return (
    <li className="grid gap-2 border-b border-[var(--theme-border)] py-3 last:border-b-0 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
      <div className="min-w-0">
        <p className="font-semibold">
          {affiliateServiceLabel(item.serviceCode)} · Cấp {item.commissionLevel}
        </p>
        <p className="text-xs text-[var(--theme-muted)]">
          {new Date(item.earnedAt).toLocaleString("vi-VN")}
        </p>
      </div>
      <div className="text-sm sm:text-right">
        <p className="font-bold">{formatVnd(item.commissionAmountMinor)}</p>
        <p className="text-xs text-[var(--theme-muted)]">
          {commissionStatusLabel(item.status)}
        </p>
      </div>
    </li>
  );
}

function ProfileStatusChangeRow({
  item,
}: {
  item: AffiliateProfileStatusChange;
}) {
  return (
    <li className="border-b border-[var(--theme-border)] py-3 last:border-b-0">
      <p className="font-semibold">
        {item.status === "SUSPENDED" ? "Đã tạm ngưng" : "Đã khôi phục"}
      </p>
      <p className="mt-1 text-xs text-[var(--theme-muted)]">
        {new Date(item.createdAt).toLocaleString("vi-VN")}
      </p>
      <p className="mt-1 break-words text-sm">{item.reason}</p>
    </li>
  );
}

export function AdminAffiliateProfiles() {
  const client = useQueryClient();
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null);
  const [action, setAction] = useState<{
    userId: string;
    kind: "suspend" | "restore";
  } | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState(false);
  const profiles = useQuery({
    queryKey: ["admin", "affiliate", "profiles", search, status, offset],
    queryFn: () =>
      adminAffiliateApi.profiles({
        search: search || undefined,
        status: status || undefined,
        offset,
      }),
  });
  const referralHistory = useQuery({
    queryKey: ["admin", "affiliate", "profile-referrals", expandedUserId],
    queryFn: () => adminAffiliateApi.profileReferrals(expandedUserId!),
    enabled: Boolean(expandedUserId),
  });
  const profileCommissions = useQuery({
    queryKey: ["admin", "affiliate", "profile-commissions", expandedUserId],
    queryFn: () =>
      adminAffiliateApi.commissions({ affiliateUserId: expandedUserId! }),
    enabled: Boolean(expandedUserId),
  });
  const statusHistory = useQuery({
    queryKey: ["admin", "affiliate", "profile-status-history", expandedUserId],
    queryFn: () => adminAffiliateApi.profileStatusHistory(expandedUserId!),
    enabled: Boolean(expandedUserId),
  });
  const setProfileStatus = useMutation({
    mutationFn: ({
      userId,
      kind,
      reason,
    }: {
      userId: string;
      kind: "suspend" | "restore";
      reason: string;
    }) =>
      kind === "suspend"
        ? adminAffiliateApi.suspend(userId, reason)
        : adminAffiliateApi.restore(userId, reason),
    onSuccess: async () => {
      setError(false);
      setAction(null);
      setReason("");
      await client.invalidateQueries({
        queryKey: ["admin", "affiliate", "profiles"],
      });
    },
    onError: () => setError(true),
  });

  const submitStatus = (profile: AdminAffiliateProfile) => {
    if (!action || reason.trim().length < 10) return;
    setError(false);
    setProfileStatus.mutate({
      userId: profile.userId,
      kind: action.kind,
      reason: reason.trim(),
    });
  };

  return (
    <section
      aria-labelledby="affiliate-profiles-title"
      className="space-y-5 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6"
    >
      <div>
        <h2
          id="affiliate-profiles-title"
          className="text-lg font-bold sm:text-xl"
        >
          Quản lý giới thiệu
        </h2>
        <p className="mt-1 text-sm text-[var(--theme-muted)]">
          Tra cứu bằng email, mã người dùng hoặc mã giới thiệu. Mọi thay đổi
          trạng thái cần có lý do lưu trong lịch sử.
        </p>
      </div>
      <form
        className="grid gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(12rem,1fr)_auto] sm:items-end"
        onSubmit={(event) => {
          event.preventDefault();
          setOffset(0);
          setSearch(searchDraft.trim());
        }}
      >
        <label
          className="grid gap-1 text-sm font-semibold"
          htmlFor="affiliate-profile-search"
        >
          Email, mã người dùng hoặc mã giới thiệu
          <input
            id="affiliate-profile-search"
            className={inputClass}
            maxLength={128}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder="Nhập mã cần tra cứu"
            value={searchDraft}
          />
        </label>
        <label
          className="grid gap-1 text-sm font-semibold"
          htmlFor="affiliate-profile-status"
        >
          Trạng thái hồ sơ
          <select
            id="affiliate-profile-status"
            className={inputClass}
            onChange={(event) => {
              setStatus(event.target.value);
              setOffset(0);
            }}
            value={status}
          >
            <option value="">Tất cả trạng thái</option>
            <option value="ACTIVE">Đang hoạt động</option>
            <option value="SUSPENDED">Tạm ngưng</option>
          </select>
        </label>
        <Button className="min-h-11" type="submit">
          Tra cứu
        </Button>
      </form>

      {profiles.isPending ? (
        <p aria-busy="true" className="py-5 text-sm" role="status">
          Đang tải hồ sơ…
        </p>
      ) : null}
      {profiles.isError ? (
        <div
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4"
          role="alert"
        >
          <p className="text-sm text-red-700">
            Chưa tải được danh sách hồ sơ. Vui lòng thử lại.
          </p>
          <Button
            className="min-h-10"
            onClick={() => void profiles.refetch()}
            type="button"
            variant="outline"
          >
            Tải lại
          </Button>
        </div>
      ) : null}
      {profiles.data?.length ? (
        <div
          aria-label="Danh sách hồ sơ giới thiệu"
          className="overflow-hidden rounded-xl border border-[var(--theme-border)]"
          role="table"
        >
          <div role="rowgroup">
            <div
              className="hidden bg-[var(--theme-elevated)] px-4 py-3 text-left text-xs font-bold uppercase tracking-wide lg:grid lg:grid-cols-[minmax(14rem,1.4fr)_minmax(15rem,1fr)_minmax(20rem,1.5fr)] lg:gap-4"
              role="row"
            >
              <span role="columnheader">Tài khoản</span>
              <span role="columnheader">Hiệu quả giới thiệu</span>
              <span role="columnheader">Trạng thái và thao tác</span>
            </div>
          </div>
          <div
            className="divide-y divide-[var(--theme-border)]"
            role="rowgroup"
          >
            {profiles.data.map((profile) => (
              <article
                className="grid gap-3 p-4 lg:grid-cols-[minmax(14rem,1.4fr)_minmax(15rem,1fr)_minmax(20rem,1.5fr)] lg:items-center lg:gap-4"
                key={profile.userId}
                role="row"
              >
                <div className="min-w-0" role="cell">
                  <p className="break-words font-semibold">{profile.email}</p>
                  <p className="mt-1 font-mono text-sm">
                    {profile.referralCode}
                  </p>
                  <p className="mt-1 break-all font-mono text-xs text-[var(--theme-muted)]">
                    Mã người dùng: {profile.userId}
                  </p>
                </div>
                <div className="min-w-0 text-sm" role="cell">
                  <span className="font-semibold lg:hidden">Hiệu quả: </span>
                  <p className="mt-1 text-xs text-[var(--theme-muted)]">
                    {profile.clickCount} lượt nhấp ·{" "}
                    {profile.attributedUserCount} người được giới thiệu · tạo
                    ngày{" "}
                    {new Date(profile.createdAt).toLocaleDateString("vi-VN")}
                  </p>
                </div>
                <div
                  className="flex flex-wrap items-center gap-2 lg:justify-end"
                  role="cell"
                >
                  <span className="text-xs font-semibold lg:hidden">
                    Trạng thái hồ sơ:
                  </span>
                  <span className="rounded-full border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-3 py-1 text-xs font-bold">
                    {profileStatusLabel(profile.status)}
                  </span>
                  <Button
                    className="min-h-10"
                    onClick={() =>
                      setExpandedUserId((current) =>
                        current === profile.userId ? null : profile.userId,
                      )
                    }
                    type="button"
                    variant="outline"
                    aria-expanded={expandedUserId === profile.userId}
                  >
                    {expandedUserId === profile.userId
                      ? "Ẩn lịch sử"
                      : "Xem lịch sử giới thiệu"}
                  </Button>
                  <Button
                    className="min-h-10"
                    onClick={() => {
                      setAction({
                        userId: profile.userId,
                        kind:
                          profile.status === "ACTIVE" ? "suspend" : "restore",
                      });
                      setReason("");
                      setError(false);
                    }}
                    type="button"
                    variant="outline"
                  >
                    {profile.status === "ACTIVE"
                      ? "Tạm ngưng hồ sơ"
                      : "Khôi phục hồ sơ"}
                  </Button>
                </div>
                {expandedUserId === profile.userId ? (
                  <section
                    aria-label={`Chi tiết giới thiệu của ${profile.email}`}
                    className="col-span-full grid gap-5 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 lg:grid-cols-2"
                    role="cell"
                  >
                    <div>
                      <h3 className="font-bold">Lượt giới thiệu</h3>
                      {referralHistory.isPending ? (
                        <p
                          aria-busy="true"
                          className="py-2 text-sm"
                          role="status"
                        >
                          Đang tải lượt giới thiệu…
                        </p>
                      ) : referralHistory.isError ? (
                        <p role="alert" className="py-2 text-sm text-red-700">
                          Chưa tải được lượt giới thiệu.
                        </p>
                      ) : referralHistory.data?.length ? (
                        <ul className="divide-y divide-[var(--theme-border)]">
                          {referralHistory.data.map((item) => (
                            <ProfileReferralRow item={item} key={item.id} />
                          ))}
                        </ul>
                      ) : (
                        <p className="py-2 text-sm text-[var(--theme-muted)]">
                          Chưa có lượt giới thiệu được ghi nhận.
                        </p>
                      )}
                    </div>
                    <div>
                      <h3 className="font-bold">Lịch sử hoa hồng</h3>
                      {profileCommissions.isPending ? (
                        <p
                          aria-busy="true"
                          className="py-2 text-sm"
                          role="status"
                        >
                          Đang tải lịch sử hoa hồng…
                        </p>
                      ) : profileCommissions.isError ? (
                        <p role="alert" className="py-2 text-sm text-red-700">
                          Chưa tải được lịch sử hoa hồng.
                        </p>
                      ) : profileCommissions.data?.length ? (
                        <ul className="divide-y divide-[var(--theme-border)]">
                          {profileCommissions.data.map((item) => (
                            <ProfileCommissionRow item={item} key={item.id} />
                          ))}
                        </ul>
                      ) : (
                        <p className="py-2 text-sm text-[var(--theme-muted)]">
                          Chưa có hoa hồng được ghi nhận.
                        </p>
                      )}
                    </div>
                    <div className="lg:col-span-2">
                      <h3 className="font-bold">Nhật ký thay đổi trạng thái</h3>
                      {statusHistory.isPending ? (
                        <p
                          aria-busy="true"
                          className="py-2 text-sm"
                          role="status"
                        >
                          Đang tải nhật ký…
                        </p>
                      ) : statusHistory.isError ? (
                        <p role="alert" className="py-2 text-sm text-red-700">
                          Chưa tải được nhật ký trạng thái.
                        </p>
                      ) : statusHistory.data?.length ? (
                        <ul className="divide-y divide-[var(--theme-border)]">
                          {statusHistory.data.map((item) => (
                            <ProfileStatusChangeRow
                              item={item}
                              key={`${item.createdAt}-${item.status}`}
                            />
                          ))}
                        </ul>
                      ) : (
                        <p className="py-2 text-sm text-[var(--theme-muted)]">
                          Chưa có thay đổi trạng thái.
                        </p>
                      )}
                    </div>
                  </section>
                ) : null}
                {action?.userId === profile.userId ? (
                  <form
                    className="col-span-full grid gap-2 border-t border-[var(--theme-border)] pt-3 sm:grid-cols-[minmax(0,1fr)_auto]"
                    role="cell"
                    onSubmit={(event) => {
                      event.preventDefault();
                      submitStatus(profile);
                    }}
                  >
                    <label className="grid gap-1 text-sm font-semibold">
                      Lý do thay đổi trạng thái (ít nhất 10 ký tự)
                      <input
                        className={inputClass}
                        minLength={10}
                        maxLength={500}
                        onChange={(event) => setReason(event.target.value)}
                        required
                        value={reason}
                      />
                    </label>
                    <Button
                      className="min-h-11 self-end"
                      disabled={
                        reason.trim().length < 10 || setProfileStatus.isPending
                      }
                      type="submit"
                    >
                      {setProfileStatus.isPending
                        ? "Đang lưu…"
                        : action.kind === "suspend"
                          ? "Xác nhận tạm ngưng"
                          : "Xác nhận khôi phục"}
                    </Button>
                  </form>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      ) : profiles.data && !profiles.data.length ? (
        <p className="rounded-xl border border-dashed border-[var(--theme-border)] p-5 text-sm text-[var(--theme-muted)]">
          Không tìm thấy hồ sơ phù hợp.
        </p>
      ) : null}

      {error ? (
        <p role="alert" className="text-sm text-red-700">
          Không cập nhật được trạng thái hồ sơ. Hãy kiểm tra lý do và quyền quản
          lý.
        </p>
      ) : null}
      {offset > 0 || profiles.data?.length === 50 ? (
        <div className="flex flex-wrap gap-2">
          {offset > 0 ? (
            <Button
              className="min-h-11"
              onClick={() => setOffset((value) => Math.max(0, value - 50))}
              type="button"
              variant="outline"
            >
              Trước đó
            </Button>
          ) : null}
          {profiles.data?.length === 50 ? (
            <Button
              className="min-h-11"
              onClick={() => setOffset((value) => value + 50)}
              type="button"
              variant="outline"
            >
              Tiếp theo
            </Button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
