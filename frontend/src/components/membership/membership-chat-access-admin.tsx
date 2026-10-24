"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CircleCheck,
  Crown,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  Search,
  ShieldCheck,
  UserPlus,
  Users,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, membershipApi } from "@/lib/api/client";
import type {
  CommunityChatRoom,
  CommunityChatRoomGrant,
  CommunityChatRoomUserCandidate,
} from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";

const rooms: { id: CommunityChatRoom; name: string; access: string }[] = [
  { id: "MEMBER", name: "Sảnh cộng đồng", access: "Mọi hạng hội viên" },
  { id: "COMPANION", name: "Phòng Đồng hành", access: "Vàng trở lên" },
  { id: "PRESTIGE", name: "Phòng Tinh hoa", access: "Kim cương" },
];

export function MembershipChatAccessAdmin() {
  const user = useAuthUser();
  const client = useQueryClient();
  const [room, setRoom] = useState<CommunityChatRoom>("COMPANION");
  const [search, setSearch] = useState("");
  const [selected, setSelected] =
    useState<CommunityChatRoomUserCandidate | null>(null);
  const [reason, setReason] = useState("");
  const [revokeTarget, setRevokeTarget] =
    useState<CommunityChatRoomGrant | null>(null);
  const [revokeReason, setRevokeReason] = useState("");
  const grantsKey = ["admin-membership-chat-access", room];
  const candidates = useQuery({
    queryKey: ["admin-membership-chat-candidates", search.trim()],
    queryFn: () => membershipApi.chatAccessUsers(search.trim()),
    enabled: search.trim().length >= 2 && !selected,
    staleTime: 15_000,
    retry: false,
  });
  const grants = useQuery({
    queryKey: grantsKey,
    queryFn: () => membershipApi.chatAccessGrants(room),
    staleTime: 15_000,
    retry: false,
  });
  const grant = useMutation({
    mutationFn: () =>
      membershipApi.grantChatAccess({
        userId: selected!.userId,
        room,
        reason: reason.trim(),
      }),
    onSuccess: async (created) => {
      setSelected(null);
      setSearch("");
      setReason("");
      await client.invalidateQueries({ queryKey: grantsKey });
      await client.invalidateQueries({
        queryKey: ["membership-chat-access", created.userId],
      });
    },
  });
  const revoke = useMutation({
    mutationFn: () =>
      membershipApi.revokeChatAccess(
        revokeTarget!.userId,
        revokeTarget!.room,
        revokeReason.trim(),
      ),
    onSuccess: async (_result, _input) => {
      const targetId = revokeTarget?.userId;
      setRevokeTarget(null);
      setRevokeReason("");
      await client.invalidateQueries({
        queryKey: ["admin-membership-chat-access"],
      });
      if (targetId) {
        await client.invalidateQueries({
          queryKey: ["membership-chat-access", targetId],
        });
      }
    },
  });
  const visibleCandidates = (candidates.data ?? []).filter(
    (candidate) =>
      !grants.data?.some(
        (activeGrant) => activeGrant.userId === candidate.userId,
      ),
  );

  return (
    <section
      aria-labelledby="membership-chat-admin-heading"
      className="relative isolate overflow-hidden rounded-[1.75rem] border border-amber-700/20 bg-gradient-to-br from-[var(--theme-surface)] via-[var(--theme-elevated)] to-[var(--theme-surface)] p-4 shadow-sm sm:p-6"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-12 -top-20 -z-10 size-64 rounded-full bg-amber-400/10 blur-3xl"
      />
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl border border-amber-700/20 bg-amber-500/10 text-amber-700">
            <KeyRound aria-hidden="true" className="size-5" />
          </span>
          <div>
            <p className="text-[0.65rem] font-bold uppercase tracking-[0.18em] text-amber-700">
              Quản lý quyền vào phòng
            </p>
            <h2
              id="membership-chat-admin-heading"
              className="mt-1 text-xl font-bold tracking-tight sm:text-2xl"
            >
              Cấp quyền thủ công
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-[var(--theme-muted)]">
              Chọn tài khoản đang hoạt động trong hệ thống và cấp quyền cho đúng
              phòng. Quyền này không đổi hạng hội viên, gói đã mua hay lịch sử
              thanh toán.
            </p>
          </div>
        </div>
        <span className="inline-flex min-h-9 items-center gap-2 rounded-full border border-emerald-700/20 bg-emerald-500/10 px-3 text-xs font-semibold text-emerald-800 dark:text-emerald-200">
          <ShieldCheck aria-hidden="true" className="size-4" /> Admin vào được
          mọi phòng
        </span>
      </header>

      <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(20rem,0.9fr)]">
        <form
          className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5"
          onSubmit={(event) => {
            event.preventDefault();
            if (selected && reason.trim().length >= 3 && !grant.isPending)
              grant.mutate();
          }}
        >
          <div className="flex items-center gap-2">
            <UserPlus aria-hidden="true" className="size-4 text-amber-700" />
            <h3 className="font-bold">Thêm thành viên vào phòng</h3>
          </div>
          <label
            className="mt-4 block text-sm font-semibold"
            htmlFor="membership-room-select"
          >
            Phòng cần cấp
          </label>
          <select
            id="membership-room-select"
            className="mt-2 min-h-12 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-3 text-base"
            value={room}
            onChange={(event) => {
              setRoom(event.target.value as CommunityChatRoom);
              setSelected(null);
              setSearch("");
              grant.reset();
            }}
          >
            {rooms.map((item) => (
              <option value={item.id} key={item.id}>
                {item.name} · {item.access}
              </option>
            ))}
          </select>
          <label
            className="mt-4 block text-sm font-semibold"
            htmlFor="membership-room-user-search"
          >
            Tìm tài khoản trong DB
          </label>
          <div className="relative mt-2">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[var(--theme-muted)]"
            />
            <input
              id="membership-room-user-search"
              className="min-h-12 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] pl-10 pr-3 text-base"
              autoComplete="off"
              maxLength={160}
              placeholder="Tên hiển thị hoặc email (từ 2 ký tự)"
              value={
                selected
                  ? `${selected.displayName} · ${selected.email}`
                  : search
              }
              onChange={(event) => {
                setSearch(event.target.value);
                setSelected(null);
                grant.reset();
              }}
            />
          </div>
          {selected ? (
            <div className="mt-2 flex items-center gap-3 rounded-xl border border-emerald-700/20 bg-emerald-500/5 p-3">
              <CircleCheck
                aria-hidden="true"
                className="size-5 shrink-0 text-emerald-700"
              />
              <span className="min-w-0 flex-1">
                <strong className="block truncate text-sm">
                  {selected.displayName}
                </strong>
                <span className="block truncate text-xs text-[var(--theme-muted)]">
                  {selected.email}
                </span>
              </span>
              <button
                className="min-h-9 px-2 text-xs font-semibold underline"
                onClick={() => {
                  setSelected(null);
                  setSearch("");
                }}
                type="button"
              >
                Đổi
              </button>
            </div>
          ) : search.trim().length >= 2 ? (
            <div className="mt-2 overflow-hidden rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)]">
              {candidates.isPending ? (
                <p
                  role="status"
                  className="flex min-h-12 items-center gap-2 px-3 text-sm text-[var(--theme-muted)]"
                >
                  <LoaderCircle
                    aria-hidden="true"
                    className="size-4 animate-spin"
                  />{" "}
                  Đang tìm tài khoản…
                </p>
              ) : candidates.isError ? (
                <p role="alert" className="p-3 text-sm text-red-700">
                  Chưa thể tìm tài khoản. Thử lại sau.
                </p>
              ) : visibleCandidates.length ? (
                <ul aria-label="Tài khoản đang hoạt động">
                  {visibleCandidates.map((candidate) => (
                    <li key={candidate.userId}>
                      <button
                        className="flex min-h-14 w-full items-center gap-3 px-3 py-2 text-left hover:bg-amber-500/5 focus-visible:bg-amber-500/10 focus-visible:outline-none"
                        onClick={() => setSelected(candidate)}
                        type="button"
                      >
                        <span className="grid size-9 shrink-0 place-items-center rounded-full bg-[var(--theme-elevated)] text-sm font-bold text-amber-800 dark:text-amber-200">
                          {candidate.displayName
                            .slice(0, 1)
                            .toLocaleUpperCase("vi-VN")}
                        </span>
                        <span className="min-w-0 flex-1">
                          <strong className="block truncate text-sm">
                            {candidate.displayName}
                          </strong>
                          <span className="block truncate text-xs text-[var(--theme-muted)]">
                            {candidate.email}
                          </span>
                        </span>
                        <span className="text-xs font-semibold text-amber-700">
                          Chọn
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="p-3 text-sm text-[var(--theme-muted)]">
                  Không tìm thấy tài khoản phù hợp hoặc họ đã có quyền trong
                  phòng này.
                </p>
              )}
            </div>
          ) : (
            <p className="mt-2 text-xs leading-5 text-[var(--theme-muted)]">
              Chỉ tìm tài khoản đang hoạt động; nhập ít nhất 2 ký tự để bắt đầu.
            </p>
          )}
          <label
            className="mt-4 block text-sm font-semibold"
            htmlFor="membership-room-grant-reason"
          >
            Lý do cấp quyền
          </label>
          <textarea
            id="membership-room-grant-reason"
            className="mt-2 min-h-24 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-3 py-2.5 text-base leading-6"
            maxLength={240}
            minLength={3}
            placeholder="Ví dụ: khách mời chương trình kết nối tháng 10"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          <div className="mt-1 flex justify-between gap-2 text-xs text-[var(--theme-muted)]">
            <span>Lưu cùng dấu vết quản trị.</span>
            <span>{reason.length}/240</span>
          </div>
          <Button
            className="mt-4 min-h-12 w-full rounded-xl"
            type="submit"
            disabled={
              !selected ||
              reason.trim().length < 3 ||
              grant.isPending ||
              grants.isError
            }
          >
            <UserPlus aria-hidden="true" className="size-4" />{" "}
            {grant.isPending ? "Đang cấp quyền…" : "Cấp quyền vào phòng"}
          </Button>
          {grant.isError ? (
            <p role="alert" className="mt-3 text-sm text-red-700">
              {grant.error instanceof ApiError
                ? grant.error.message
                : "Chưa thể cấp quyền. Vui lòng thử lại."}
            </p>
          ) : null}
          {grant.isSuccess ? (
            <p role="status" className="mt-3 text-sm text-emerald-700">
              Đã cấp quyền vào phòng.
            </p>
          ) : null}
        </form>

        <section
          aria-labelledby="membership-room-grants-heading"
          className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <Users aria-hidden="true" className="size-4 text-amber-700" />
              <h3 id="membership-room-grants-heading" className="font-bold">
                Quyền cấp thêm
              </h3>
            </div>
            <span className="rounded-full bg-[var(--theme-elevated)] px-3 py-1 text-xs font-semibold">
              {rooms.find((item) => item.id === room)?.name}
            </span>
          </div>
          <p className="mt-1 text-xs leading-5 text-[var(--theme-muted)]">
            Các quyền bổ sung đang hiệu lực. Thu hồi không ảnh hưởng đến hạng
            hội viên đã mua.
          </p>
          {grants.isPending ? (
            <p role="status" className="mt-5 text-sm text-[var(--theme-muted)]">
              Đang tải danh sách quyền…
            </p>
          ) : grants.isError ? (
            <p role="alert" className="mt-5 text-sm text-red-700">
              Chưa tải được quyền phòng. Cấp quyền đang tạm khóa.
            </p>
          ) : grants.data?.length ? (
            <ul className="mt-4 divide-y divide-[var(--theme-border)]">
              {grants.data.map((item) => (
                <li className="py-4" key={`${item.userId}-${item.room}`}>
                  <div className="flex items-start gap-3">
                    <span className="grid size-9 shrink-0 place-items-center rounded-full bg-amber-500/10 text-xs font-bold text-amber-800 dark:text-amber-200">
                      {item.displayName.slice(0, 1).toLocaleUpperCase("vi-VN")}
                    </span>
                    <div className="min-w-0 flex-1">
                      <strong className="block truncate text-sm">
                        {item.displayName}
                      </strong>
                      <span className="block truncate text-xs text-[var(--theme-muted)]">
                        {item.email}
                      </span>
                      <p className="mt-2 text-xs leading-5 text-[var(--theme-muted)]">
                        Lý do: {item.reason}
                      </p>
                      <p className="mt-1 text-[0.68rem] text-[var(--theme-muted)]">
                        Cấp ngày{" "}
                        {new Date(item.grantedAt).toLocaleDateString("vi-VN")}
                      </p>
                    </div>
                    {revokeTarget?.userId === item.userId &&
                    revokeTarget.room === item.room ? null : (
                      <button
                        className="min-h-9 shrink-0 rounded-lg px-2 text-xs font-semibold text-[var(--theme-muted)] underline hover:text-red-700"
                        onClick={() => {
                          setRevokeTarget(item);
                          setRevokeReason("");
                          revoke.reset();
                        }}
                        type="button"
                      >
                        Thu hồi
                      </button>
                    )}
                  </div>
                  {revokeTarget?.userId === item.userId &&
                  revokeTarget.room === item.room ? (
                    <div className="mt-3 rounded-xl border border-red-700/20 bg-red-500/5 p-3">
                      <label
                        className="block text-xs font-semibold"
                        htmlFor={`revoke-reason-${item.userId}`}
                      >
                        Lý do thu hồi
                      </label>
                      <input
                        id={`revoke-reason-${item.userId}`}
                        className="mt-2 min-h-10 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm"
                        maxLength={240}
                        minLength={3}
                        value={revokeReason}
                        onChange={(event) =>
                          setRevokeReason(event.target.value)
                        }
                      />
                      <div className="mt-2 flex flex-wrap justify-end gap-2">
                        <Button
                          variant="outline"
                          className="min-h-10"
                          onClick={() => setRevokeTarget(null)}
                          type="button"
                        >
                          Giữ quyền
                        </Button>
                        <Button
                          className="min-h-10 bg-red-700 text-white hover:bg-red-800"
                          disabled={
                            revokeReason.trim().length < 3 || revoke.isPending
                          }
                          onClick={() => revoke.mutate()}
                          type="button"
                        >
                          {revoke.isPending
                            ? "Đang thu hồi…"
                            : "Xác nhận thu hồi"}
                        </Button>
                      </div>
                      {revoke.isError ? (
                        <p role="alert" className="mt-2 text-xs text-red-700">
                          {revoke.error instanceof ApiError
                            ? revoke.error.message
                            : "Chưa thể thu hồi quyền."}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <div className="mt-5 flex min-h-32 flex-col items-center justify-center rounded-xl border border-dashed border-[var(--theme-border)] px-4 text-center">
              <LockKeyhole
                aria-hidden="true"
                className="size-5 text-[var(--theme-muted)]"
              />
              <p className="mt-2 text-sm font-semibold">
                Chưa có quyền cấp thêm
              </p>
              <p className="mt-1 text-xs text-[var(--theme-muted)]">
                Hội viên đủ hạng và admin vẫn vào phòng theo quyền mặc định.
              </p>
            </div>
          )}
          {revoke.isSuccess ? (
            <p role="status" className="mt-3 text-sm text-emerald-700">
              Đã thu hồi quyền vào phòng.
            </p>
          ) : null}
        </section>
      </div>
    </section>
  );
}
