"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftRight, Inbox, LoaderCircle } from "lucide-react";
import { useState } from "react";

import { similarityApi, staffAccountsApi } from "@/lib/api/client";
import type { SimilarityCase } from "@/lib/api/types";

function AssignmentRow({ item }: { item: SimilarityCase }) {
  const queryClient = useQueryClient();
  const [reviewerId, setReviewerId] = useState("");
  const reviewers = useQuery({
    queryKey: ["staff-accounts", "active-reviewers"],
    queryFn: () =>
      staffAccountsApi.list({
        role: "MODERATOR",
        status: "ACTIVE",
        pageSize: 100,
      }),
  });
  const assign = useMutation({
    mutationFn: () => similarityApi.assign(item.id, reviewerId),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["similarity-cases"] }),
  });

  return (
    <article className="grid gap-5 border-b border-neutral-100 px-5 py-6 last:border-0 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.55fr)] lg:items-end">
      <div>
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-amber-700">
          <ArrowLeftRight aria-hidden="true" className="size-4" />
          Chờ phân công đối chiếu
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {[item.leftAsset, item.rightAsset].map((asset, index) => (
            <div className="border-l-2 border-neutral-200 pl-4" key={index}>
              <h2 className="font-bold text-neutral-950">
                {asset?.dossierTitle ?? "Hồ sơ được bảo vệ"}
              </h2>
              <p className="mt-1 text-sm text-neutral-500">
                {asset
                  ? `${asset.dossierCode} · Phiên bản ${asset.versionNo}`
                  : "Thông tin giới hạn"}
              </p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm leading-6 text-neutral-600">
          {item.signalType === "IMAGE"
            ? "Hệ thống ghi nhận hình ảnh cần được chuyên gia đối chiếu."
            : "Hệ thống ghi nhận nội dung cần được chuyên gia đối chiếu."}
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
        <label className="text-sm font-bold text-neutral-800">
          Chuyên gia phụ trách
          <select
            className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 font-medium"
            onChange={(event) => setReviewerId(event.target.value)}
            value={reviewerId}
          >
            <option value="">Chọn người xử lý</option>
            {reviewers.data?.data.map((reviewer) => (
              <option key={reviewer.id} value={reviewer.id}>
                {reviewer.email}
              </option>
            ))}
          </select>
        </label>
        <button
          className="min-h-11 rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white hover:bg-primary-700 disabled:opacity-50"
          disabled={!reviewerId || assign.isPending}
          onClick={() => assign.mutate()}
          type="button"
        >
          {assign.isPending ? "Đang giao…" : "Giao xử lý"}
        </button>
        {assign.isError ? (
          <p
            className="text-sm font-semibold text-red-700 sm:col-span-2"
            role="alert"
          >
            Chưa thể giao xử lý. Vui lòng thử lại.
          </p>
        ) : null}
      </div>
    </article>
  );
}

export function SimilarityCaseQueue() {
  const cases = useQuery({
    queryKey: ["similarity-cases", "admin", "open"],
    queryFn: () => similarityApi.listAdmin({ status: "OPEN", pageSize: 50 }),
  });
  if (cases.isPending)
    return (
      <div className="grid min-h-56 place-items-center" role="status">
        <LoaderCircle className="size-7 animate-spin" />
        <span className="sr-only">Đang tải danh sách phân công</span>
      </div>
    );
  if (cases.isError)
    return (
      <div
        className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm font-semibold text-red-800"
        role="alert"
      >
        Chưa thể tải danh sách phân công.
      </div>
    );
  if (!cases.data.data.length)
    return (
      <div className="rounded-2xl border border-dashed bg-white px-6 py-14 text-center">
        <Inbox className="mx-auto size-9 text-neutral-400" />
        <h2 className="mt-4 text-xl font-bold">
          Không có trường hợp chờ phân công
        </h2>
      </div>
    );
  return (
    <div className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      {cases.data.data.map((item) => (
        <AssignmentRow item={item} key={item.id} />
      ))}
    </div>
  );
}
