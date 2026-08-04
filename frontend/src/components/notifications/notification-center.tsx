"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";

import { notificationApi } from "@/lib/api/client";

export function NotificationCenter() {
  const client = useQueryClient();
  const notifications = useQuery({ queryKey: ["notifications"], queryFn: () => notificationApi.list() });
  const markRead = useMutation({ mutationFn: notificationApi.markRead, onSuccess: async () => client.invalidateQueries({ queryKey: ["notifications"] }) });
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header><p className="flex items-center gap-2 text-sm font-bold text-primary-700"><Bell className="size-4" />Trung tâm cập nhật</p><h1 className="mt-2 text-3xl font-bold">Thông báo</h1><p className="mt-2 text-sm text-neutral-600">Các thay đổi quan trọng trong hồ sơ và quy trình của bạn.</p></header>
      <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        {notifications.isPending ? <p className="p-6" role="status">Đang tải thông báo...</p> : null}
        {notifications.data?.data.length === 0 ? <div className="p-10 text-center"><Bell className="mx-auto size-8 text-neutral-300" /><h2 className="mt-3 font-bold">Chưa có thông báo</h2><p className="mt-1 text-sm text-neutral-500">Thông báo nghiệp vụ mới sẽ xuất hiện tại đây.</p></div> : null}
        <div className="divide-y divide-neutral-100">{notifications.data?.data.map((item) => <article className={item.readAt ? "p-5" : "bg-primary-50/50 p-5"} key={item.id}><div className="flex gap-4"><div className="min-w-0 flex-1"><h2 className="font-bold">{item.title}</h2><p className="mt-1 text-sm leading-6 text-neutral-600">{item.body}</p><time className="mt-2 block text-xs text-neutral-400">{new Date(item.createdAt).toLocaleString("vi-VN")}</time></div>{!item.readAt ? <button aria-label={`Đánh dấu đã đọc: ${item.title}`} className="grid size-10 shrink-0 place-items-center rounded-xl border border-neutral-200 bg-white text-primary-700" onClick={() => markRead.mutate(item.id)} type="button"><CheckCheck className="size-4" /></button> : null}</div></article>)}</div>
      </section>
    </div>
  );
}
