"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";

import { adminCertificateApi } from "@/lib/api/client";
import type { CertificateContent } from "@/lib/api/types";

export function CertificateContentCorrection({
  certificateId,
}: {
  certificateId: string;
}) {
  const queryClient = useQueryClient();
  const current = useQuery({
    queryKey: ["admin", "certificate-content", certificateId],
    queryFn: () => adminCertificateApi.issuedContent(certificateId),
  });
  const [form, setForm] = useState<CertificateContent | null>(null);
  const [reason, setReason] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const correction = useMutation({
    mutationFn: (input: {
      expectedVersionNo: number;
      reason: string;
      content: CertificateContent;
    }) => adminCertificateApi.requestContentCorrection(certificateId, input),
    onSuccess: async () => {
      setSubmitted(true);
      await queryClient.invalidateQueries({
        queryKey: ["admin", "certificate-version-requests"],
      });
    },
  });
  const content = form ?? current.data?.content;
  const dirty = Boolean(
    content &&
      current.data &&
      JSON.stringify(content) !== JSON.stringify(current.data.content),
  );

  if (current.isPending) {
    return (
      <p className="flex items-center gap-2 text-sm" role="status">
        <LoaderCircle className="size-4 animate-spin" /> Đang tải nội dung bằng…
      </p>
    );
  }
  if (current.isError || !current.data || !content) {
    return (
      <p className="text-sm text-red-700" role="alert">
        Không thể tải nội dung bằng để chỉnh sửa.
      </p>
    );
  }

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          correction.mutate({
            expectedVersionNo: current.data.currentVersionNo,
            reason: reason.trim(),
            content,
          });
        }}
      >
        <p className="font-mono text-sm font-bold text-primary-700">
          {current.data.certificateNumber}
        </p>
        <p className="text-xs text-neutral-600">
          Phiên bản hiện tại: {current.data.currentVersionNo}. Phiên bản cũ được
          giữ lại để đối chiếu.
        </p>
        <label className="block text-sm font-bold">
          Tên tác phẩm
          <input
            className="mt-1 min-h-11 w-full rounded-lg border border-neutral-300 bg-white px-3"
            maxLength={255}
            required
            value={content.title}
            onChange={(event) => setForm({ ...content, title: event.target.value })}
          />
        </label>
        <label className="block text-sm font-bold">
          Tác giả / người được ghi nhận
          <input
            className="mt-1 min-h-11 w-full rounded-lg border border-neutral-300 bg-white px-3"
            maxLength={255}
            value={content.subject}
            onChange={(event) =>
              setForm({ ...content, subject: event.target.value })
            }
          />
        </label>
        <button
          className="text-xs underline"
          onClick={() => setForm({ ...content, subject: "" })}
          type="button"
        >
          Xóa tên người được ghi nhận
        </button>
        <label className="block text-sm font-bold">
          Danh mục
          <input
            className="mt-1 min-h-11 w-full rounded-lg border border-neutral-300 bg-white px-3"
            maxLength={255}
            required
            value={content.category}
            onChange={(event) =>
              setForm({ ...content, category: event.target.value })
            }
          />
        </label>
        <label className="block text-sm font-bold">
          Mô tả tác phẩm
          <textarea
            className="mt-1 min-h-28 w-full rounded-lg border border-neutral-300 bg-white p-3"
            maxLength={5000}
            value={content.summary}
            onChange={(event) =>
              setForm({ ...content, summary: event.target.value })
            }
          />
        </label>
        <button
          className="text-xs underline"
          onClick={() => setForm({ ...content, summary: "" })}
          type="button"
        >
          Xóa mô tả
        </button>
        <label className="block text-sm font-bold">
          Lý do chỉnh sửa
          <textarea
            className="mt-1 min-h-24 w-full rounded-lg border border-neutral-300 bg-white p-3"
            maxLength={2000}
            minLength={20}
            required
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
        <button
          className="min-h-11 rounded-lg bg-[#720b17] px-4 font-bold text-white disabled:opacity-50"
          disabled={
            !dirty ||
            !content.title.trim() ||
            !content.category.trim() ||
            reason.trim().length < 20 ||
            correction.isPending ||
            submitted
          }
          type="submit"
        >
          {correction.isPending ? "Đang gửi…" : "Gửi duyệt phiên bản mới"}
        </button>
        {correction.isError ? (
          <p className="text-sm text-red-700" role="alert">
            Không thể gửi yêu cầu. Bằng có thể đã thay đổi; hãy tải lại trang.
          </p>
        ) : null}
        {submitted ? (
          <p className="text-sm text-emerald-800" role="status">
            Đã gửi duyệt. Bằng hiện tại vẫn có hiệu lực trong lúc chờ quản trị viên khác phê duyệt. PDF mới sẽ được tạo sau khi duyệt.
          </p>
        ) : null}
      </form>
      <div
        aria-label="Xem trước nội dung phiên bản mới"
        className="self-start border-2 border-[#b7882f] bg-[#fffdf5] p-5"
      >
        <p className="text-xs font-bold uppercase tracking-widest text-[#9b7427]">
          Xem trước nội dung
        </p>
        <h3 className="mt-3 text-xl font-bold">BẰNG XÁC LẬP</h3>
        <p className="mt-4 break-words text-xl font-bold">{content.title}</p>
        {content.summary ? (
          <p className="mt-3 whitespace-pre-wrap text-sm">{content.summary}</p>
        ) : null}
        {content.subject ? (
          <p className="mt-3 text-sm">Người được ghi nhận: {content.subject}</p>
        ) : null}
        <p className="mt-3 text-sm">Danh mục: {content.category}</p>
      </div>
    </div>
  );
}
