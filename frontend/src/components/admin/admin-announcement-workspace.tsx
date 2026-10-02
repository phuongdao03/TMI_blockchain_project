"use client";

import { BellRing, CheckCircle2, Search, Send, UsersRound } from "lucide-react";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  adminAnnouncementsApi,
  adminUsersApi,
  ApiError,
} from "@/lib/api/client";
import type { AdminUser, AnnouncementAudience } from "@/lib/api/types";

const audiences: {
  value: AnnouncementAudience;
  label: string;
  detail: string;
}[] = [
  {
    value: "ALL",
    label: "Toàn hệ thống",
    detail: "Tất cả tài khoản đang hoạt động",
  },
  {
    value: "USERS",
    label: "Người dùng",
    detail: "Tài khoản không có hồ sơ nhân viên đang làm việc",
  },
  {
    value: "EMPLOYEES",
    label: "Nhân viên",
    detail: "Tài khoản có hồ sơ nhân viên đang làm việc",
  },
  {
    value: "INDIVIDUAL",
    label: "Một người",
    detail: "Chọn một tài khoản cụ thể",
  },
];

const fieldClass =
  "w-full rounded-xl border border-neutral-200 bg-white px-4 py-3 text-neutral-950 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100";

export function AdminAnnouncementWorkspace() {
  const [audience, setAudience] = useState<AnnouncementAudience>("ALL");
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [search, setSearch] = useState("");
  const [matches, setMatches] = useState<AdminUser[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [recipientCount, setRecipientCount] = useState<number | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<number | null>(null);
  const [campaignId, setCampaignId] = useState(() => crypto.randomUUID());

  function resetDraftConfirmation() {
    setRecipientCount(null);
    setConfirmed(false);
    setReceipt(null);
    setCampaignId(crypto.randomUUID());
  }

  async function findUsers() {
    setError(null);
    setBusy(true);
    try {
      const result = await adminUsersApi.list({
        search: search.trim() || undefined,
        status: "ACTIVE",
        pageSize: 20,
      });
      setMatches(result.data);
    } catch (cause) {
      setError(
        cause instanceof ApiError ? cause.message : "Không thể tìm tài khoản.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function preview() {
    setError(null);
    setBusy(true);
    try {
      const result = await adminAnnouncementsApi.preview({
        audience,
        recipientUserId:
          audience === "INDIVIDUAL" ? selectedUser?.id : undefined,
      });
      setRecipientCount(result.recipientCount);
      setConfirmed(false);
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Không thể xem số người nhận.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !confirmed ||
      !recipientCount ||
      title.trim().length < 3 ||
      body.trim().length < 3
    )
      return;
    setError(null);
    setBusy(true);
    try {
      const result = await adminAnnouncementsApi.send({
        audience,
        recipientUserId:
          audience === "INDIVIDUAL" ? selectedUser?.id : undefined,
        campaignId,
        title: title.trim(),
        body: body.trim(),
      });
      setReceipt(result.recipientCount);
      setRecipientCount(null);
      setConfirmed(false);
      setTitle("");
      setBody("");
      setCampaignId(crypto.randomUUID());
    } catch (cause) {
      setError(
        cause instanceof ApiError ? cause.message : "Không thể gửi thông báo.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <header className="rounded-3xl border border-neutral-200 bg-white p-6 sm:p-8">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-primary-600">
          <BellRing aria-hidden="true" className="size-4" /> Trung tâm thông báo
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-neutral-950">
          Gửi thông báo
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-700">
          Thông báo xuất hiện trong ứng dụng, ở chuông và trang Thông báo của
          người nhận.
        </p>
      </header>
      {receipt !== null ? (
        <p
          className="flex items-center gap-3 rounded-2xl border border-emerald-300 bg-emerald-50 p-4 text-emerald-900"
          role="status"
        >
          <CheckCircle2 aria-hidden="true" className="size-5" /> Đã gửi cho{" "}
          {receipt.toLocaleString("vi-VN")} tài khoản.
        </p>
      ) : null}
      {error ? (
        <p
          className="rounded-2xl border border-error bg-primary-50 p-4 text-sm text-error"
          role="alert"
        >
          {error}
        </p>
      ) : null}

      <form className="space-y-6" onSubmit={send}>
        <section
          className="rounded-3xl border border-neutral-200 bg-white p-5 sm:p-7"
          aria-labelledby="audience-heading"
        >
          <div className="mb-5 flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-xl bg-primary-50 text-primary-700">
              <UsersRound aria-hidden="true" className="size-5" />
            </span>
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
                01 · Người nhận
              </p>
              <h2
                id="audience-heading"
                className="text-xl font-bold text-neutral-950"
              >
                Chọn phạm vi gửi
              </h2>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {audiences.map((item) => (
              <button
                key={item.value}
                type="button"
                aria-pressed={audience === item.value}
                className={
                  "rounded-2xl border p-4 text-left transition focus-visible:outline-2 focus-visible:outline-primary-500 " +
                  (audience === item.value
                    ? "border-primary-600 bg-primary-50"
                    : "border-neutral-200 hover:border-primary-300")
                }
                onClick={() => {
                  setAudience(item.value);
                  setSelectedUser(null);
                  resetDraftConfirmation();
                }}
              >
                <span className="font-bold text-neutral-950">{item.label}</span>
                <span className="mt-1 block text-sm leading-5 text-neutral-700">
                  {item.detail}
                </span>
              </button>
            ))}
          </div>
          {audience === "INDIVIDUAL" ? (
            <div className="mt-5 rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
              <label
                htmlFor="announcement-user-search"
                className="mb-2 block text-sm font-semibold text-neutral-950"
              >
                Tìm tài khoản
              </label>
              <div className="flex gap-2">
                <input
                  id="announcement-user-search"
                  className={fieldClass}
                  placeholder="Tên hoặc email"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      void findUsers();
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  disabled={busy}
                  onClick={findUsers}
                >
                  <Search aria-hidden="true" className="size-4" />
                  Tìm
                </Button>
              </div>
              {selectedUser ? (
                <p className="mt-3 text-sm font-semibold text-primary-700">
                  Đã chọn: {selectedUser.fullName || selectedUser.email} ·{" "}
                  {selectedUser.email}
                </p>
              ) : null}
              {matches.length ? (
                <ul
                  className="mt-3 max-h-56 space-y-2 overflow-y-auto"
                  aria-label="Tài khoản tìm thấy"
                >
                  {matches.map((user) => (
                    <li key={user.id}>
                      <button
                        type="button"
                        className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-left text-sm hover:border-primary-500"
                        onClick={() => {
                          setSelectedUser(user);
                          setMatches([]);
                          resetDraftConfirmation();
                        }}
                      >
                        {user.fullName || user.email}
                        <span className="block text-neutral-500">
                          {user.email}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </section>

        <section
          className="rounded-3xl border border-neutral-200 bg-white p-5 sm:p-7"
          aria-labelledby="content-heading"
        >
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
            02 · Nội dung
          </p>
          <h2
            id="content-heading"
            className="mt-1 text-xl font-bold text-neutral-950"
          >
            Soạn thông báo
          </h2>
          <label
            htmlFor="announcement-title"
            className="mt-5 block text-sm font-semibold text-neutral-950"
          >
            Tiêu đề
          </label>
          <input
            id="announcement-title"
            className={"mt-2 " + fieldClass}
            maxLength={255}
            required
            minLength={3}
            value={title}
            onChange={(event) => {
              setTitle(event.target.value);
              resetDraftConfirmation();
            }}
            placeholder="Ví dụ: Cập nhật lịch làm việc tháng 10"
          />
          <label
            htmlFor="announcement-body"
            className="mt-5 block text-sm font-semibold text-neutral-950"
          >
            Nội dung
          </label>
          <textarea
            id="announcement-body"
            className={"mt-2 min-h-36 resize-y " + fieldClass}
            maxLength={5000}
            required
            minLength={3}
            value={body}
            onChange={(event) => {
              setBody(event.target.value);
              resetDraftConfirmation();
            }}
            placeholder="Viết thông tin người nhận cần biết..."
          />
          <p className="mt-1 text-right text-xs tabular-nums text-neutral-500">
            {body.length.toLocaleString("vi-VN")} / 5.000 ký tự
          </p>
        </section>

        <section
          className="rounded-3xl border border-neutral-200 bg-white p-5 sm:p-7"
          aria-labelledby="confirm-heading"
        >
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
            03 · Kiểm tra & gửi
          </p>
          <h2
            id="confirm-heading"
            className="mt-1 text-xl font-bold text-neutral-950"
          >
            Xác nhận người nhận
          </h2>
          <p className="mt-2 text-sm text-neutral-700">
            Hệ thống tính lại phạm vi tại thời điểm gửi.
          </p>
          <Button
            className="mt-5"
            type="button"
            variant="outline"
            disabled={
              busy ||
              (audience === "INDIVIDUAL" && !selectedUser) ||
              title.trim().length < 3 ||
              body.trim().length < 3
            }
            onClick={preview}
          >
            Xem số người nhận
          </Button>
          {recipientCount !== null ? (
            <p
              className="mt-4 rounded-xl bg-neutral-50 p-4 text-sm font-semibold text-neutral-950"
              role="status"
            >
              {recipientCount.toLocaleString("vi-VN")} tài khoản sẽ nhận thông
              báo.
            </p>
          ) : null}
          {recipientCount !== null && recipientCount > 0 ? (
            <label className="mt-4 flex cursor-pointer items-start gap-3 text-sm text-neutral-700">
              <input
                className="mt-1 size-4 accent-primary-600"
                type="checkbox"
                checked={confirmed}
                onChange={(event) => setConfirmed(event.target.checked)}
              />
              Tôi đã kiểm tra nội dung và phạm vi người nhận.
            </label>
          ) : null}
          <div className="mt-6 flex justify-end border-t border-neutral-200 pt-5">
            <Button
              type="submit"
              disabled={busy || !confirmed || !recipientCount}
            >
              <Send aria-hidden="true" className="size-4" />
              {busy ? "Đang xử lý…" : "Gửi thông báo"}
            </Button>
          </div>
        </section>
      </form>
    </div>
  );
}
