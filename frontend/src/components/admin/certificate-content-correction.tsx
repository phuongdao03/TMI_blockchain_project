"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";

import { adminCertificateApi, publicWorkAdminApi } from "@/lib/api/client";
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
  const categories = useQuery({
    queryKey: ["admin", "public-work-categories"],
    queryFn: publicWorkAdminApi.categories,
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
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["admin", "certificate-content", certificateId],
        }),
        queryClient.invalidateQueries({ queryKey: ["admin", "certificates"] }),
      ]);
    },
  });
  const content = form ?? current.data?.content;
  const dirty = Boolean(
    content &&
      current.data &&
      JSON.stringify(content) !== JSON.stringify(current.data.content),
  );
  const activeCategories =
    categories.data?.filter((item) => item.isActive) ?? [];
  const categorySelected = activeCategories.some(
    (item) => item.name === content?.category,
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
    <div className="grid min-w-0 gap-5 lg:grid-cols-2">
      <form
        className="min-w-0 space-y-4"
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
            onChange={(event) =>
              setForm({ ...content, title: event.target.value })
            }
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
          <select
            className="mt-1 min-h-11 w-full rounded-lg border border-neutral-300 bg-white px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600"
            disabled={categories.isPending || categories.isError}
            required
            value={categorySelected ? content.category : ""}
            onChange={(event) =>
              setForm({ ...content, category: event.target.value })
            }
          >
            <option value="">Chọn danh mục đã có</option>
            {activeCategories.map((category) => (
              <option key={category.id} value={category.name}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        {!categories.isPending && !categorySelected && content.category ? (
          <p className="text-xs text-amber-800">
            Danh mục trên phiên bản cũ: {content.category}. Hãy chọn danh mục
            hiện đang dùng trong hệ thống.
          </p>
        ) : null}
        {categories.isError ? (
          <p className="text-sm text-red-700" role="alert">
            Không tải được danh mục. Hãy tải lại trang.
          </p>
        ) : null}
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
            !categorySelected ||
            reason.trim().length < 20 ||
            correction.isPending ||
            submitted
          }
          type="submit"
        >
          {correction.isPending
            ? "Đang lưu…"
            : "Lưu và phát hành bản điều chỉnh"}
        </button>
        {correction.isError ? (
          <p className="text-sm text-red-700" role="alert">
            Không thể lưu bản điều chỉnh. Bằng có thể đã thay đổi; hãy tải lại
            trang.
          </p>
        ) : null}
        {submitted ? (
          <p className="text-sm text-emerald-800" role="status">
            Đã phát hành phiên bản mới. Trang xác minh dùng nội dung vừa lưu;
            PDF mới đang được tạo và sẽ sẵn sàng để tải sau khi xử lý xong.
          </p>
        ) : null}
      </form>
      <div
        aria-label="Xem trước nội dung phiên bản mới"
        className="self-start border-2 border-[#b7882f] bg-[#fffdf5] p-5"
      >
        <p className="text-xs font-bold uppercase tracking-widest text-[#9b7427]">
          Nội dung chung cho trang xác minh và PDF
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
        <div className="mt-5 grid gap-3 border-t border-[#d8c798] pt-4 text-xs leading-5 sm:grid-cols-2">
          <p>
            <strong className="block text-[#720b17]">Trang xác minh</strong>
            Nội dung mới hiển thị công khai cùng số bằng và trạng thái.
          </p>
          <p>
            <strong className="block text-[#720b17]">PDF tải về</strong>
            PDF cùng phiên bản được tạo lại sau khi lưu.
          </p>
        </div>
      </div>
    </div>
  );
}
