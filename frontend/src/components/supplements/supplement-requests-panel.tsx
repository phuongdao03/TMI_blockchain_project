"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { supplementApi, type SupplementRequest } from "@/lib/api/supplements";
import { useAuthUser } from "@/lib/auth/user-context";

const statuses = {
  OPEN: "Cần phản hồi",
  ANSWERED: "Đã phản hồi, chờ kiểm tra",
  RESOLVED: "Đã xử lý",
};
const entries = {
  RESPONSE: "Phản hồi người nộp",
  RESOLVE: "Kết quả kiểm tra",
  REOPEN: "Yêu cầu làm rõ thêm",
};
const inputClass =
  "mt-1 min-h-24 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 text-sm font-normal";

export function SupplementRequestsPanel({
  dossierId,
  mode,
  canRespond = false,
  versionId,
  criteria = [],
  onOpenChange,
}: {
  dossierId: string;
  mode: "applicant" | "reviewer";
  canRespond?: boolean;
  versionId?: string;
  criteria?: Array<{ key: string; label: string }>;
  onOpenChange?: (hasOpenRequests: boolean) => void;
}) {
  const user = useAuthUser();
  const queryClient = useQueryClient();
  const key = ["supplement-requests", user?.id, dossierId];
  const query = useQuery({
    queryKey: key,
    queryFn: () => supplementApi.list(dossierId),
    enabled: Boolean(user),
  });
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [criterion, setCriterion] = useState("");
  const [information, setInformation] = useState("");
  const [reason, setReason] = useState("");
  const [priority, setPriority] = useState<"NORMAL" | "HIGH">("NORMAL");
  const [deadline, setDeadline] = useState("");
  const [message, setMessage] = useState("");
  const dirty = Boolean(
    information ||
      reason ||
      Object.values(drafts).some((value) => value.trim()),
  );
  useEffect(() => {
    if (query.data)
      onOpenChange?.(query.data.some((item) => item.status === "OPEN"));
  }, [query.data, onOpenChange]);
  useEffect(() => {
    if (!dirty) return;
    const beforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    const beforeNavigate = (event: MouseEvent) => {
      const anchor =
        event.target instanceof Element
          ? event.target.closest("a[href]")
          : null;
      if (!anchor || anchor.getAttribute("href")?.startsWith("#")) return;
      event.preventDefault();
      event.stopPropagation();
      setMessage("Gửi hoặc hủy nội dung chưa lưu trước khi chuyển trang.");
    };
    window.addEventListener("beforeunload", beforeUnload);
    document.addEventListener("click", beforeNavigate, true);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
      document.removeEventListener("click", beforeNavigate, true);
    };
  }, [dirty]);
  const action = useMutation({
    mutationFn: async ({
      kind,
      item,
    }: {
      kind: "respond" | "resolve" | "reopen";
      item: SupplementRequest;
    }) => {
      const content = drafts[item.id] ?? "";
      return kind === "respond"
        ? supplementApi.respond(dossierId, item, content)
        : supplementApi.decide(dossierId, item, content, kind === "reopen");
    },
    onSuccess: (item) => {
      setDrafts((current) => ({ ...current, [item.id]: "" }));
      setMessage("Đã ghi nhận nội dung.");
      void queryClient.invalidateQueries({ queryKey: key });
    },
    onError: () =>
      setMessage(
        "Chưa thể ghi nhận. Nội dung được giữ lại; tải lại yêu cầu nếu phiên bản đã thay đổi.",
      ),
  });
  const create = useMutation({
    mutationFn: () =>
      supplementApi.create(dossierId, {
        expectedVersionId: versionId!,
        criterionKey: criterion,
        requestedInformation: information,
        reason,
        priority,
        dueAt: deadline ? new Date(deadline).toISOString() : null,
      }),
    onSuccess: () => {
      setInformation("");
      setReason("");
      setMessage(
        "Đã lưu yêu cầu. Người nộp nhận yêu cầu khi hồ sơ được mở bổ sung theo quy trình hiện hành.",
      );
      void queryClient.invalidateQueries({ queryKey: key });
    },
    onError: () =>
      setMessage(
        "Chưa thể tạo yêu cầu. Kiểm tra phân công, phiên bản và nội dung; các thông tin đã nhập được giữ lại.",
      ),
  });
  if (!user) return null;
  return (
    <section
      aria-label="Yêu cầu bổ sung có cấu trúc"
      className="space-y-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6"
    >
      <h2 className="text-lg font-bold">Yêu cầu bổ sung và phản hồi</h2>
      <p className="text-sm leading-6 text-[var(--theme-muted)]">
        Mỗi yêu cầu gắn với tiêu chí và phiên bản đã nộp. Phản hồi được lưu
        trong lịch sử; việc trả lời chưa đồng nghĩa nội dung đã được chấp nhận.
      </p>
      {query.isPending ? (
        <p role="status">Đang tải yêu cầu…</p>
      ) : query.isError ? (
        <div role="alert">
          <p>Chưa tải được yêu cầu bổ sung.</p>
          <Button
            type="button"
            variant="outline"
            onClick={() => void query.refetch()}
          >
            Thử tải lại yêu cầu
          </Button>
        </div>
      ) : query.data?.length === 0 ? (
        <p className="text-sm text-[var(--theme-muted)]">
          Chưa có yêu cầu bổ sung được công bố cho bạn.
        </p>
      ) : null}
      {query.data?.map((item, index) => (
        <article
          key={item.id}
          className="space-y-3 border-t border-[var(--theme-border)] pt-4"
        >
          <div className="flex flex-wrap justify-between gap-2">
            <h3 className="font-semibold">
              {index + 1}. {item.criterionLabel}
            </h3>
            <span className="text-sm font-semibold">
              {statuses[item.status]}
            </span>
          </div>
          <p className="whitespace-pre-wrap break-words text-sm leading-6">
            {item.requestedInformation}
          </p>
          <p className="whitespace-pre-wrap break-words text-sm text-[var(--theme-muted)]">
            Lý do: {item.reason}
          </p>
          <p className="text-sm text-[var(--theme-muted)]">
            Ưu tiên: {item.priority === "HIGH" ? "Cao" : "Thông thường"}
            {item.dueAt
              ? ` · Hạn phản hồi: ${new Date(item.dueAt).toLocaleString("vi-VN")}`
              : " · Chưa ấn định hạn phản hồi"}
          </p>
          {item.responses.map((entry) => (
            <div
              className="border-l-2 border-[var(--theme-border)] pl-3 text-sm"
              key={entry.id}
            >
              <p className="font-semibold">{entries[entry.kind]}</p>
              <p className="whitespace-pre-wrap break-words leading-6">
                {entry.text}
              </p>
            </div>
          ))}
          {(mode === "applicant" && canRespond && item.status === "OPEN") ||
          mode === "reviewer" ? (
            <fieldset className="space-y-2" disabled={action.isPending}>
              <label className="block text-sm font-semibold">
                {mode === "applicant"
                  ? "Giải trình hoặc nội dung đã bổ sung"
                  : "Nhận định xử lý yêu cầu"}
                <textarea
                  aria-label={`Nội dung xử lý yêu cầu ${index + 1}`}
                  className={inputClass}
                  value={drafts[item.id] ?? ""}
                  maxLength={2000}
                  onChange={(event) =>
                    setDrafts((current) => ({
                      ...current,
                      [item.id]: event.target.value,
                    }))
                  }
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  disabled={(drafts[item.id]?.trim().length ?? 0) < 20}
                  onClick={() =>
                    action.mutate({
                      kind:
                        mode === "applicant"
                          ? "respond"
                          : item.status === "RESOLVED"
                            ? "reopen"
                            : "resolve",
                      item,
                    })
                  }
                >
                  {mode === "applicant"
                    ? "Gửi phản hồi"
                    : item.status === "RESOLVED"
                      ? "Mở lại yêu cầu"
                      : "Xác nhận đã xử lý"}
                </Button>
                {drafts[item.id] ? (
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() =>
                      setDrafts((current) => ({ ...current, [item.id]: "" }))
                    }
                  >
                    Hủy nội dung đang nhập
                  </Button>
                ) : null}
              </div>
            </fieldset>
          ) : null}
        </article>
      ))}
      {mode === "reviewer" && versionId && criteria.length > 0 ? (
        <details className="border-t border-[var(--theme-border)] pt-4">
          <summary className="cursor-pointer font-semibold">
            Tạo yêu cầu bổ sung theo tiêu chí
          </summary>
          <fieldset disabled={create.isPending} className="mt-3 space-y-3">
            <label className="block text-sm font-semibold">
              Tiêu chí cần bổ sung
              <select
                className="mt-1 min-h-11 w-full rounded-lg border bg-[var(--theme-surface)] px-3"
                value={criterion}
                onChange={(event) => setCriterion(event.target.value)}
              >
                <option value="">Chọn tiêu chí</option>
                {criteria.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-semibold">
              Thông tin cần bổ sung
              <textarea
                className={inputClass}
                maxLength={2000}
                value={information}
                onChange={(event) => setInformation(event.target.value)}
              />
            </label>
            <label className="block text-sm font-semibold">
              Lý do cần bổ sung
              <textarea
                className={inputClass}
                maxLength={2000}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-sm font-semibold">
                Mức ưu tiên
                <select
                  className="mt-1 min-h-11 w-full rounded-lg border bg-[var(--theme-surface)] px-3"
                  value={priority}
                  onChange={(event) =>
                    setPriority(event.target.value as "NORMAL" | "HIGH")
                  }
                >
                  <option value="NORMAL">Thông thường</option>
                  <option value="HIGH">Cao</option>
                </select>
              </label>
              <label className="min-w-0 text-sm font-semibold">
                Hạn phản hồi (nếu được quy định)
                <input
                  type="datetime-local"
                  className="mt-1 min-h-11 w-full rounded-lg border bg-[var(--theme-surface)] px-3"
                  value={deadline}
                  onChange={(event) => setDeadline(event.target.value)}
                />
              </label>
            </div>
            <Button
              type="button"
              disabled={
                !criterion ||
                information.trim().length < 20 ||
                reason.trim().length < 20
              }
              onClick={() => create.mutate()}
            >
              Lưu yêu cầu bổ sung
            </Button>
            {information || reason ? (
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setInformation("");
                  setReason("");
                }}
              >
                Hủy yêu cầu đang soạn
              </Button>
            ) : null}
          </fieldset>
        </details>
      ) : null}
      {message ? (
        <p role="status" className="text-sm font-semibold">
          {message}
        </p>
      ) : null}
    </section>
  );
}
