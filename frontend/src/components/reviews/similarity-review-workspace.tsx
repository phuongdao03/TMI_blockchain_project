"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Inbox,
  LoaderCircle,
} from "lucide-react";
import { type FormEvent, useState } from "react";

import { mediaApi, similarityApi } from "@/lib/api/client";
import type {
  SimilarityCase,
  SimilarityCaseDisposition,
} from "@/lib/api/types";

const dispositions: Array<{
  value: SimilarityCaseDisposition;
  label: string;
}> = [
  { value: "DISTINCT", label: "Hai tác phẩm độc lập" },
  { value: "RELATED", label: "Có liên quan nhưng là hai tác phẩm riêng" },
  { value: "SAME_WORK", label: "Cùng một tác phẩm" },
];

function AssetPanel({
  item,
  side,
}: {
  item: SimilarityCase;
  side: "left" | "right";
}) {
  const asset = side === "left" ? item.leftAsset : item.rightAsset;
  const evidence = useMutation({
    mutationFn: mediaApi.signedUrl,
    onSuccess: ({ url }) => window.open(url, "_blank", "noopener,noreferrer"),
  });
  return (
    <div className="min-w-0 border-l-2 border-neutral-200 pl-4 first:border-primary-500">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-neutral-500">
        {side === "left" ? "Hồ sơ đối chiếu A" : "Hồ sơ đối chiếu B"}
      </p>
      <h3 className="mt-2 truncate text-lg font-bold text-neutral-950">
        {asset?.dossierTitle ?? "Hồ sơ đang được bảo vệ"}
      </h3>
      <p className="mt-1 text-sm text-neutral-500">
        {asset
          ? `${asset.dossierCode} · Phiên bản ${asset.versionNo}`
          : "Thông tin giới hạn"}
      </p>
      {asset?.evidenceMediaIds.map((mediaId, index) => (
        <button
          className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800 hover:border-primary-300 hover:text-primary-700 disabled:opacity-50"
          disabled={evidence.isPending}
          key={mediaId}
          onClick={() => evidence.mutate(mediaId)}
          type="button"
        >
          <ExternalLink aria-hidden="true" className="size-4" />
          Xem tài liệu {index + 1}
        </button>
      ))}
      {evidence.isError ? (
        <p className="mt-2 text-sm font-semibold text-red-700" role="alert">
          Chưa thể mở tài liệu bảo mật.
        </p>
      ) : null}
    </div>
  );
}

function ReviewCase({ item }: { item: SimilarityCase }) {
  const queryClient = useQueryClient();
  const [disposition, setDisposition] =
    useState<SimilarityCaseDisposition>("DISTINCT");
  const [reason, setReason] = useState("");
  const resolve = useMutation({
    mutationFn: () =>
      similarityApi.resolve(item.id, { disposition, reason: reason.trim() }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["similarity-cases"] });
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (reason.trim().length >= 20) resolve.mutate();
  }

  return (
    <article className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      <div className="flex flex-col gap-3 border-b border-neutral-100 bg-neutral-50/70 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="flex items-center gap-2 text-sm font-bold text-amber-800">
          <AlertTriangle aria-hidden="true" className="size-4" />
          {item.signalType === "IMAGE"
            ? "Hình ảnh có dấu hiệu tương đồng"
            : "Nội dung có dấu hiệu tương đồng"}
        </p>
        <span className="text-xs font-semibold text-neutral-500">
          Cần chuyên gia đối chiếu trước khi tiếp tục
        </span>
      </div>

      <div className="grid gap-6 p-5 md:grid-cols-2 md:p-6">
        <AssetPanel item={item} side="left" />
        <AssetPanel item={item} side="right" />
      </div>

      <details className="border-y border-neutral-100 px-5 py-3 text-sm text-neutral-600 md:px-6">
        <summary className="cursor-pointer font-semibold text-neutral-800">
          Xem căn cứ hệ thống gợi ý đối chiếu
        </summary>
        <p className="mt-3 max-w-3xl leading-6">
          {item.signalType === "IMAGE"
            ? `Khoảng cách hình ảnh: ${item.imageDistance ?? "chưa xác định"}/64.`
            : `Mức tương đồng nội dung: ${Math.round((item.textScore ?? 0) * 100)}%.`}{" "}
          Đây chỉ là tín hiệu hỗ trợ, không phải kết luận về tính xác thực hay
          quyền sở hữu.
        </p>
      </details>

      {item.status === "RESOLVED" ? (
        <div className="flex gap-3 p-5 text-sm text-emerald-800 md:p-6">
          <CheckCircle2 aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-bold">Đã hoàn tất đối chiếu</p>
            <p className="mt-1 leading-6 text-neutral-600">
              {item.resolutionReason}
            </p>
          </div>
        </div>
      ) : (
        <form
          className="grid gap-5 p-5 md:grid-cols-[minmax(0,0.8fr)_minmax(0,1.4fr)_auto] md:items-end md:p-6"
          onSubmit={submit}
        >
          <label className="text-sm font-bold text-neutral-800">
            Kết luận đối chiếu
            <select
              className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 font-medium outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
              onChange={(event) =>
                setDisposition(event.target.value as SimilarityCaseDisposition)
              }
              value={disposition}
            >
              {dispositions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-bold text-neutral-800">
            Căn cứ cho kết luận
            <textarea
              className="mt-2 min-h-24 w-full resize-y rounded-xl border border-neutral-300 bg-white px-3 py-2 font-medium outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
              maxLength={2000}
              minLength={20}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Nêu rõ những điểm đã kiểm tra và cơ sở đưa ra kết luận."
              required
              value={reason}
            />
          </label>
          <button
            className="min-h-11 rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white transition hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={reason.trim().length < 20 || resolve.isPending}
            type="submit"
          >
            {resolve.isPending ? "Đang lưu…" : "Hoàn tất đối chiếu"}
          </button>
          {resolve.isError ? (
            <p
              className="text-sm font-semibold text-red-700 md:col-span-3"
              role="alert"
            >
              Chưa thể lưu kết luận. Vui lòng kiểm tra và thử lại.
            </p>
          ) : null}
        </form>
      )}
    </article>
  );
}

export function SimilarityReviewWorkspace() {
  const cases = useQuery({
    queryKey: ["similarity-cases", "reviewer"],
    queryFn: () => similarityApi.listReviewer({ pageSize: 20 }),
  });

  if (cases.isPending) {
    return (
      <div className="grid min-h-64 place-items-center" role="status">
        <LoaderCircle className="size-7 animate-spin" />
        <span className="sr-only">Đang tải danh sách đối chiếu</span>
      </div>
    );
  }
  if (cases.isError) {
    return (
      <div
        className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm font-semibold text-red-800"
        role="alert"
      >
        Chưa thể tải danh sách đối chiếu. Vui lòng thử lại.
      </div>
    );
  }
  if (!cases.data.data.length) {
    return (
      <div className="rounded-2xl border border-dashed border-neutral-300 bg-white px-6 py-14 text-center">
        <Inbox aria-hidden="true" className="mx-auto size-9 text-neutral-400" />
        <h2 className="mt-4 text-xl font-bold">
          Chưa có nội dung cần đối chiếu
        </h2>
        <p className="mt-2 text-sm text-neutral-500">
          Danh sách sẽ cập nhật khi bạn được phân công một trường hợp mới.
        </p>
      </div>
    );
  }
  return (
    <div className="space-y-5">
      {cases.data.data.map((item) => (
        <ReviewCase item={item} key={item.id} />
      ))}
    </div>
  );
}
