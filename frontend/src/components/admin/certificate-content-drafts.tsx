"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";

import { adminCertificateApi, publicWorkAdminApi } from "@/lib/api/client";
import type { CertificateContent } from "@/lib/api/types";

export function CertificateContentDrafts() {
  const queryClient = useQueryClient();
  const drafts = useQuery({
    queryKey: ["admin", "certificate-content-drafts"],
    queryFn: adminCertificateApi.contentDrafts,
  });
  const categories = useQuery({
    queryKey: ["admin", "public-work-categories"],
    queryFn: publicWorkAdminApi.categories,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<CertificateContent | null>(null);
  const save = useMutation({
    mutationFn: (input: { dossierId: string; content: CertificateContent }) =>
      adminCertificateApi.updateContentDraft(input.dossierId, input.content),
    onSuccess: async (updated, variables) => {
      if (selectedId === variables.dossierId) {
        setForm(updated.content);
      }
      await queryClient.invalidateQueries({
        queryKey: ["admin", "certificate-content-drafts"],
      });
    },
  });
  const confirm = useMutation({
    mutationFn: adminCertificateApi.confirmContentDraft,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["admin", "certificate-content-drafts"],
      });
    },
  });
  const selected = drafts.data?.find((draft) => draft.dossierId === selectedId);
  const content = form ?? selected?.content;
  const dirty = Boolean(
    selected &&
      content &&
      JSON.stringify(content) !== JSON.stringify(selected.content),
  );
  const activeCategories =
    categories.data?.filter((item) => item.isActive) ?? [];
  const categorySelected = activeCategories.some(
    (item) => item.name === content?.category,
  );

  return (
    <section
      className="rounded-2xl border border-[#d8c798] bg-[#fffdf5] p-4 text-[#2b1714] sm:p-6"
      aria-labelledby="certificate-drafts-title"
    >
      <h2
        id="certificate-drafts-title"
        className="text-xl font-bold text-[#2b1714]"
      >
        Duyệt nội dung bằng xác lập trước khi phát hành
      </h2>
      <p className="mt-2 text-sm leading-6 text-[#6d5949]">
        Chỉnh nội dung sẽ in trên PDF và hiển thị trên trang xác minh. Sau khi
        phát hành, bản ghi đã xác thực không thể sửa trực tiếp.
      </p>
      {drafts.isPending ? (
        <p className="mt-5 flex items-center gap-2 text-sm" role="status">
          <LoaderCircle className="size-4 animate-spin" /> Đang tải bản nháp…
        </p>
      ) : drafts.isError ? (
        <p className="mt-5 text-sm text-red-700" role="alert">
          Không tải được bản nháp. Vui lòng thử lại.
        </p>
      ) : drafts.data?.length === 0 ? (
        <p className="mt-5 text-sm">Chưa có bằng xác lập cần duyệt nội dung.</p>
      ) : (
        <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(12rem,17rem)_minmax(0,1fr)]">
          <div className="space-y-2" aria-label="Hồ sơ chờ duyệt nội dung">
            {drafts.data?.map((draft) => (
              <button
                key={draft.dossierId}
                type="button"
                className={`w-full rounded-xl border px-4 py-3 text-left text-sm ${draft.dossierId === selectedId ? "border-[#9b7427] bg-[#f8f0dc]" : "border-[#e1d5b5] bg-white"}`}
                onClick={() => {
                  setSelectedId(draft.dossierId);
                  setForm({ ...draft.content });
                }}
              >
                <span className="block font-bold">{draft.dossierTitle}</span>
                <span className="mt-1 block font-mono text-xs">
                  {draft.dossierCode}
                </span>
                <span className="mt-1 block text-xs">
                  {draft.confirmedAt
                    ? "Đã xác nhận · chờ phát hành"
                    : "Chờ chỉnh và xác nhận"}
                </span>
              </button>
            ))}
          </div>
          {selected && content ? (
            <div className="grid gap-5 xl:grid-cols-2">
              <form
                className="space-y-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  save.mutate({ dossierId: selected.dossierId, content });
                }}
              >
                <label className="block text-sm font-bold">
                  Tên tác phẩm
                  <input
                    className="mt-1 min-h-11 w-full rounded-lg border border-[#c9ad60] bg-white px-3"
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
                    className="mt-1 min-h-11 w-full rounded-lg border border-[#c9ad60] bg-white px-3"
                    maxLength={255}
                    value={content.subject}
                    onChange={(event) =>
                      setForm({ ...content, subject: event.target.value })
                    }
                  />
                </label>
                <button
                  type="button"
                  className="text-xs underline"
                  onClick={() => setForm({ ...content, subject: "" })}
                >
                  Xóa tên người được ghi nhận
                </button>
                <label className="block text-sm font-bold">
                  Danh mục
                  <select
                    className="mt-1 min-h-11 w-full rounded-lg border border-[#c9ad60] bg-white px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600"
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
                {!categories.isPending &&
                !categorySelected &&
                content.category ? (
                  <p className="text-xs text-amber-800">
                    Danh mục cũ: {content.category}. Hãy chọn danh mục đang hoạt
                    động.
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
                    className="mt-1 min-h-28 w-full rounded-lg border border-[#c9ad60] bg-white p-3"
                    maxLength={5000}
                    value={content.summary}
                    onChange={(event) =>
                      setForm({ ...content, summary: event.target.value })
                    }
                  />
                </label>
                <button
                  type="button"
                  className="text-xs underline"
                  onClick={() => setForm({ ...content, summary: "" })}
                >
                  Xóa mô tả
                </button>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="submit"
                    disabled={
                      !dirty ||
                      !categorySelected ||
                      save.isPending ||
                      confirm.isPending
                    }
                    className="min-h-11 rounded-lg border border-[#9b7427] px-4 font-bold disabled:opacity-50"
                  >
                    {save.isPending ? "Đang lưu…" : "Lưu nội dung"}
                  </button>
                  <button
                    type="button"
                    disabled={
                      dirty ||
                      !content.title.trim() ||
                      !categorySelected ||
                      confirm.isPending ||
                      save.isPending
                    }
                    onClick={() => confirm.mutate(selected.dossierId)}
                    className="min-h-11 rounded-lg bg-[#720b17] px-4 font-bold text-white disabled:opacity-50"
                  >
                    {confirm.isPending
                      ? "Đang xác nhận…"
                      : "Xác nhận phát hành"}
                  </button>
                </div>
                {save.isError || confirm.isError ? (
                  <p role="alert" className="text-sm text-red-700">
                    Chưa lưu được thay đổi. Vui lòng tải lại và thử lại.
                  </p>
                ) : null}
              </form>
              <div
                className="self-start border-2 border-[#b7882f] bg-white p-5 text-[#2b1714]"
                aria-label="Xem trước nội dung bằng xác lập"
              >
                <p className="text-xs font-bold uppercase tracking-widest text-[#9b7427]">
                  Nội dung chung cho trang xác minh và PDF
                </p>
                <h3 className="mt-3 text-xl font-bold">BẰNG XÁC LẬP</h3>
                <p className="mt-5 text-xs text-[#9b7427]">
                  TÁC PHẨM ĐƯỢC GHI NHẬN
                </p>
                <p className="mt-2 break-words text-2xl font-bold">
                  {content.title || "Tên tác phẩm"}
                </p>
                {content.summary ? (
                  <p className="mt-4 text-sm leading-6">{content.summary}</p>
                ) : null}
                {content.subject ? (
                  <p className="mt-4 text-sm">
                    <strong>Người được ghi nhận:</strong> {content.subject}
                  </p>
                ) : null}
                <p className="mt-3 text-sm">
                  <strong>Danh mục:</strong> {content.category || "Chưa có"}
                </p>
                <div className="mt-5 grid gap-3 border-t border-[#d8c798] pt-4 text-xs leading-5 sm:grid-cols-2">
                  <p>
                    <strong className="block text-[#720b17]">
                      Trang xác minh
                    </strong>
                    Hiển thị công khai sau khi bằng được phát hành.
                  </p>
                  <p>
                    <strong className="block text-[#720b17]">PDF tải về</strong>
                    Được tạo từ cùng nội dung đã xác nhận.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm">Chọn một hồ sơ để chỉnh nội dung.</p>
          )}
        </div>
      )}
    </section>
  );
}
