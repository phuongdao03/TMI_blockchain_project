"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BadgeCheck,
  CheckCircle2,
  CircleAlert,
  FileCheck2,
  FileText,
  Fingerprint,
  LoaderCircle,
  LockKeyhole,
  Save,
  Send,
  Trash2,
  UploadCloud,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import {
  dossierStatusLabel,
  DossierStatusBadge,
} from "@/components/dossiers/dossier-status";
import { DossierWorkflowTimeline } from "@/components/dossiers/dossier-workflow-timeline";
import { FileUploader } from "@/components/media/file-uploader";
import { DossierPaymentAction } from "@/components/payments/dossier-payment-action";
import { PrivateDocumentVerification } from "@/components/documents/private-document-verification";
import { Button } from "@/components/ui/button";
import { dossierApi } from "@/lib/api/client";
import type {
  DossierDetail,
  DossierEvidence,
  DossierStatus,
  MediaAsset,
} from "@/lib/api/types";
import { dossierKeys } from "@/lib/dossiers/query-keys";
import { cn } from "@/lib/utils";

const infoSchema = z.object({
  title: z.string().trim().min(3).max(255),
  summary: z.string().trim().max(10_000),
  visibility: z.enum(["PRIVATE", "UNLISTED", "PUBLIC"]),
});

type InfoValues = z.infer<typeof infoSchema>;
type Step = "information" | "evidence" | "review";

const steps: Array<{
  id: Step;
  label: string;
  description: string;
  icon: typeof FileText;
}> = [
  {
    id: "information",
    label: "Thông tin",
    description: "Mô tả tài sản",
    icon: FileText,
  },
  {
    id: "evidence",
    label: "Bằng chứng",
    description: "Tài liệu đã tải lên",
    icon: UploadCloud,
  },
  {
    id: "review",
    label: "Kiểm tra & nộp",
    description: "Xác nhận nội dung",
    icon: FileCheck2,
  },
];

const dossierGuidance: Record<
  DossierStatus,
  { outcome: string; next: string }
> = {
  DRAFT: {
    outcome: "Hồ sơ đang được bạn chuẩn bị.",
    next: "Hoàn thiện thông tin và thêm ít nhất một tài liệu.",
  },
  SUBMITTED: {
    outcome: "TMI đã nhận hồ sơ.",
    next: "Theo dõi thông báo trong khi hồ sơ được kiểm tra.",
  },
  PRECHECK: {
    outcome: "Hồ sơ đang được kiểm tra ban đầu.",
    next: "Bạn chưa cần làm gì thêm lúc này.",
  },
  NEEDS_SUPPLEMENT: {
    outcome: "Hồ sơ cần thêm tài liệu hoặc thông tin.",
    next: "Mở phần được yêu cầu, bổ sung và nộp lại hồ sơ.",
  },
  UNDER_REVIEW: {
    outcome: "Hồ sơ đang được thẩm định.",
    next: "Theo dõi thông báo và phản hồi nếu có yêu cầu mới.",
  },
  COUNCIL_REVIEW: {
    outcome: "Kết quả thẩm định đang được xem xét.",
    next: "Bạn chưa cần làm gì thêm lúc này.",
  },
  APPROVED: {
    outcome: "Hồ sơ đã đủ điều kiện phát hành.",
    next: "Thanh toán phí phát hành để tiếp tục.",
  },
  REJECTED: {
    outcome: "Hồ sơ hiện chưa đủ điều kiện.",
    next: "Xem thông báo kết quả hoặc liên hệ hỗ trợ khi cần giải thích.",
  },
  PAYMENT_PENDING: {
    outcome: "Hồ sơ đang chờ hoàn tất lệ phí.",
    next: "Mở lại trang thanh toán hoặc chờ trạng thái được cập nhật.",
  },
  PAID: {
    outcome: "Khoản phí đã được xác nhận.",
    next: "Chờ TMI chuẩn bị chứng thư.",
  },
  ANCHOR_PENDING: {
    outcome: "Chứng thư đang được chuẩn bị.",
    next: "Theo dõi thông báo phát hành.",
  },
  ANCHORED: {
    outcome: "Chứng thư đã sẵn sàng để phát hành.",
    next: "Chờ thông báo tải chứng thư.",
  },
  CERTIFICATE_ISSUED: {
    outcome: "Chứng thư đã được phát hành.",
    next: "Mở danh sách chứng thư để tải xuống.",
  },
  PUBLISHED: {
    outcome: "Chứng thư đã được công bố.",
    next: "Tải chứng thư hoặc chia sẻ đường dẫn kiểm tra.",
  },
  REVOKED: {
    outcome: "Chứng thư không còn hiệu lực.",
    next: "Liên hệ hỗ trợ nếu bạn cần biết thêm lý do.",
  },
  CANCELLED: {
    outcome: "Hồ sơ đã được hủy.",
    next: "Tạo hồ sơ mới nếu bạn muốn bắt đầu lại.",
  },
};

function formatBytes(bytes: number) {
  return new Intl.NumberFormat("vi-VN", {
    maximumFractionDigits: 1,
  }).format(bytes / 1024);
}

function newIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() ?? `submit-${Date.now()}`;
}

function EvidenceItem({
  canEdit,
  evidence,
  onRemove,
}: {
  canEdit: boolean;
  evidence: DossierEvidence;
  onRemove: (id: string) => void;
}) {
  return (
    <article className="grid gap-4 rounded-xl border border-neutral-200 bg-white p-4 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center">
      <span className="grid size-11 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
        <FileCheck2 aria-hidden="true" className="size-5" />
      </span>
      <div className="min-w-0">
        <h3 className="truncate text-sm font-bold text-neutral-950">
          {evidence.title}
        </h3>
        <p className="mt-1 text-xs text-neutral-500">
          {evidence.mimeType} · {formatBytes(evidence.bytes)} KB
        </p>
      </div>
      {canEdit ? (
        <Button
          aria-label={`Xóa ${evidence.title}`}
          className="text-red-700 hover:bg-red-50"
          onClick={() => onRemove(evidence.id)}
          variant="ghost"
        >
          <Trash2 aria-hidden="true" className="size-4" />
          Xóa
        </Button>
      ) : (
        <span className="inline-flex items-center gap-1.5 text-xs font-bold text-neutral-500">
          <LockKeyhole aria-hidden="true" className="size-4" />
          Đã khóa
        </span>
      )}
      <PrivateDocumentVerification mediaId={evidence.mediaAssetId} />
    </article>
  );
}

function InformationStep({ dossier }: { dossier: DossierDetail }) {
  const form = useForm<InfoValues>({
    resolver: zodResolver(infoSchema),
    defaultValues: {
      title: dossier.title,
      summary: dossier.summary ?? "",
      visibility: dossier.visibility,
    },
  });
  const queryClient = useQueryClient();
  const values = useWatch({ control: form.control });
  const update = useMutation({
    mutationFn: (next: InfoValues) =>
      dossierApi.update(dossier.id, {
        title: next.title,
        summary: next.summary || null,
        visibility: next.visibility,
      }),
    onSuccess: (saved) => {
      queryClient.setQueryData(dossierKeys.detail(dossier.id), {
        ...dossier,
        ...saved,
        evidences: dossier.evidences,
      });
      form.reset({
        title: saved.title,
        summary: saved.summary ?? "",
        visibility: saved.visibility,
      });
    },
  });
  const save = update.mutate;

  useEffect(() => {
    if (!dossier.canEdit || !form.formState.isDirty || update.isPending) return;
    const parsed = infoSchema.safeParse(values);
    if (!parsed.success) return;
    const timeout = window.setTimeout(() => save(parsed.data), 700);
    return () => window.clearTimeout(timeout);
  }, [dossier.canEdit, form.formState.isDirty, save, update.isPending, values]);

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Thông tin hồ sơ</h2>
          <p className="mt-1 text-sm text-neutral-500">
            Thay đổi hợp lệ được tự động lưu sau vài giây.
          </p>
        </div>
        <span
          className="inline-flex min-h-8 items-center gap-2 rounded-full bg-neutral-100 px-3 text-xs font-bold text-neutral-600"
          role="status"
        >
          {update.isPending ? (
            <LoaderCircle
              aria-hidden="true"
              className="size-3.5 animate-spin"
            />
          ) : (
            <Save aria-hidden="true" className="size-3.5" />
          )}
          {update.isPending ? "Đang lưu…" : "Tự động lưu"}
        </span>
      </div>
      <div>
        <label className="text-sm font-bold" htmlFor="workspace-title">
          Tên hồ sơ
        </label>
        <input
          className="mt-2 min-h-12 w-full rounded-xl border border-neutral-200 px-4 text-sm outline-none focus:border-primary-500 focus:ring-4 focus:ring-primary-100 disabled:bg-neutral-100 disabled:text-neutral-500"
          disabled={!dossier.canEdit}
          id="workspace-title"
          {...form.register("title")}
        />
      </div>
      <div>
        <label className="text-sm font-bold" htmlFor="workspace-summary">
          Mô tả
        </label>
        <textarea
          className="mt-2 min-h-40 w-full resize-y rounded-xl border border-neutral-200 px-4 py-3 text-sm leading-6 outline-none focus:border-primary-500 focus:ring-4 focus:ring-primary-100 disabled:bg-neutral-100 disabled:text-neutral-500"
          disabled={!dossier.canEdit}
          id="workspace-summary"
          {...form.register("summary")}
        />
      </div>
      <div>
        <label className="text-sm font-bold" htmlFor="workspace-visibility">
          Chế độ hiển thị
        </label>
        <select
          className="mt-2 min-h-12 w-full rounded-xl border border-neutral-200 bg-white px-4 text-sm outline-none focus:border-primary-500 focus:ring-4 focus:ring-primary-100 disabled:bg-neutral-100"
          disabled={!dossier.canEdit}
          id="workspace-visibility"
          {...form.register("visibility")}
        >
          <option value="PRIVATE">Riêng tư</option>
          <option value="UNLISTED">Không niêm yết</option>
          <option value="PUBLIC">Công khai sau cấp chứng thư</option>
        </select>
      </div>
      {update.error ? (
        <p
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800"
          role="alert"
        >
          Tự động lưu chưa thành công. Dữ liệu vẫn còn trên biểu mẫu.
        </p>
      ) : null}
    </section>
  );
}

export function DossierWorkspace({ dossierId }: { dossierId: string }) {
  const [step, setStep] = useState<Step>("information");
  const [evidenceTitle, setEvidenceTitle] = useState("Tài liệu chứng minh");
  const [evidenceType, setEvidenceType] = useState("OWNERSHIP_DOCUMENT");
  const queryClient = useQueryClient();
  const detail = useQuery({
    queryKey: dossierKeys.detail(dossierId),
    queryFn: () => dossierApi.get(dossierId),
  });
  const versions = useQuery({
    queryKey: dossierKeys.versions(dossierId),
    queryFn: () => dossierApi.versions(dossierId),
  });
  const timeline = useQuery({
    queryKey: dossierKeys.timeline(dossierId),
    queryFn: () => dossierApi.timeline(dossierId),
  });
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: dossierKeys.detail(dossierId),
      }),
      queryClient.invalidateQueries({
        queryKey: dossierKeys.versions(dossierId),
      }),
      queryClient.invalidateQueries({
        queryKey: dossierKeys.timeline(dossierId),
      }),
      queryClient.invalidateQueries({ queryKey: dossierKeys.lists() }),
    ]);
  };
  const attach = useMutation({
    mutationFn: (asset: MediaAsset) =>
      dossierApi.attachEvidence(dossierId, {
        mediaAssetId: asset.id,
        evidenceType,
        title: evidenceTitle.trim() || "Tài liệu chứng minh",
        displayOrder: detail.data?.evidences.length ?? 0,
        isPublic: false,
      }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (evidenceId: string) =>
      dossierApi.removeEvidence(dossierId, evidenceId),
    onSuccess: refresh,
  });
  const submit = useMutation({
    mutationFn: async () => {
      const key = newIdempotencyKey();
      return detail.data?.status === "NEEDS_SUPPLEMENT"
        ? dossierApi.resubmit(dossierId, key)
        : dossierApi.submit(dossierId, key);
    },
    onSuccess: refresh,
  });

  if (detail.isPending) {
    return (
      <div className="grid min-h-[60vh] place-items-center" role="status">
        <span className="flex items-center gap-3 font-semibold text-neutral-600">
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          Đang mở hồ sơ…
        </span>
      </div>
    );
  }
  if (detail.error || !detail.data) {
    return (
      <div
        className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800"
        role="alert"
      >
        Không thể mở hồ sơ. Vui lòng quay lại danh sách và thử lại.
      </div>
    );
  }

  const dossier = detail.data;
  const isComplete = dossier.evidences.length > 0 && dossier.title.length >= 3;
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div className="min-w-0">
          <Link
            className="inline-flex min-h-11 items-center gap-2 text-sm font-bold text-neutral-500 hover:text-primary-700"
            href="/dossiers"
          >
            <ArrowLeft aria-hidden="true" className="size-4" />
            Danh sách hồ sơ
          </Link>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <DossierStatusBadge status={dossier.status} />
            <span className="font-mono text-xs font-bold tracking-wider text-neutral-400">
              {dossier.code}
            </span>
          </div>
          <h1 className="mt-3 truncate text-3xl font-bold tracking-[-0.03em] text-neutral-950 sm:text-4xl">
            {dossier.title}
          </h1>
        </div>
        <div className="rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm">
          <p className="font-bold text-neutral-900">
            Phiên bản hiện tại: {dossier.currentVersionNo || "Chưa nộp"}
          </p>
          <p className="mt-1 text-xs text-neutral-500">
            Mỗi lần nộp được lưu thành một phiên bản riêng.
          </p>
        </div>
      </div>

      <section className="grid gap-2 border-l-4 border-primary-600 bg-primary-50 px-5 py-4 text-sm text-primary-950 sm:grid-cols-[1fr_1fr] sm:gap-8">
        <div>
          <p className="font-bold">Trạng thái hiện tại</p>
          <p className="mt-1 leading-6">
            {dossierGuidance[dossier.status].outcome}
          </p>
        </div>
        <div>
          <p className="font-bold">Việc tiếp theo</p>
          <p className="mt-1 leading-6">
            {dossierGuidance[dossier.status].next}
          </p>
        </div>
      </section>

      {!dossier.canEdit ? (
        <div className="flex items-start gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
          <LockKeyhole aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-bold">Hồ sơ đã nộp và đang ở chế độ chỉ đọc.</p>
            <p className="mt-1 leading-6 text-blue-800">
              Bạn vẫn có thể xem phiên bản và lịch sử. Chỉnh sửa chỉ mở lại khi
              hồ sơ được yêu cầu bổ sung.
            </p>
          </div>
        </div>
      ) : null}

      <DossierPaymentAction
        dossierId={dossier.id}
        dossierStatus={dossier.status}
      />

      <DossierWorkflowTimeline
        history={timeline.data ?? []}
        status={dossier.status}
      />

      <div className="grid gap-6 xl:grid-cols-[17rem_minmax(0,1fr)]">
        <nav
          aria-label="Các bước hoàn thiện hồ sơ"
          className="h-fit rounded-2xl border border-neutral-200 bg-white p-2 xl:sticky xl:top-24"
        >
          {steps.map((item, index) => {
            const Icon = item.icon;
            const active = item.id === step;
            return (
              <button
                aria-current={active ? "step" : undefined}
                className={cn(
                  "flex min-h-16 w-full items-center gap-3 rounded-xl px-3 text-left transition",
                  active
                    ? "bg-primary-50 text-primary-800"
                    : "text-neutral-600 hover:bg-neutral-50",
                )}
                key={item.id}
                onClick={() => setStep(item.id)}
                type="button"
              >
                <span
                  className={cn(
                    "grid size-9 shrink-0 place-items-center rounded-lg",
                    active
                      ? "bg-primary-600 text-white"
                      : "bg-neutral-100 text-neutral-500",
                  )}
                >
                  <Icon aria-hidden="true" className="size-4" />
                </span>
                <span>
                  <span className="block text-sm font-bold">
                    {index + 1}. {item.label}
                  </span>
                  <span className="mt-0.5 block text-xs opacity-70">
                    {item.description}
                  </span>
                </span>
              </button>
            );
          })}
        </nav>

        <div className="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-7 lg:p-8">
          {step === "information" ? (
            <InformationStep dossier={dossier} />
          ) : null}

          {step === "evidence" ? (
            <section className="space-y-6">
              <div>
                <h2 className="text-xl font-bold tracking-tight">
                  Bằng chứng hồ sơ
                </h2>
                <p className="mt-1 text-sm leading-6 text-neutral-500">
                  Thêm tài liệu giúp chứng minh nguồn gốc, quyền sở hữu hoặc quá
                  trình hình thành tác phẩm.
                </p>
              </div>
              {dossier.canEdit ? (
                <div className="grid gap-4 rounded-2xl border border-neutral-200 bg-neutral-50 p-4 sm:grid-cols-2">
                  <div>
                    <label
                      className="text-sm font-bold"
                      htmlFor="evidence-title"
                    >
                      Tên bằng chứng
                    </label>
                    <input
                      className="mt-2 min-h-11 w-full rounded-xl border border-neutral-200 bg-white px-3 text-sm"
                      id="evidence-title"
                      onChange={(event) => setEvidenceTitle(event.target.value)}
                      value={evidenceTitle}
                    />
                  </div>
                  <div>
                    <label
                      className="text-sm font-bold"
                      htmlFor="evidence-type"
                    >
                      Loại bằng chứng
                    </label>
                    <select
                      className="mt-2 min-h-11 w-full rounded-xl border border-neutral-200 bg-white px-3 text-sm"
                      id="evidence-type"
                      onChange={(event) => setEvidenceType(event.target.value)}
                      value={evidenceType}
                    >
                      <option value="OWNERSHIP_DOCUMENT">
                        Tài liệu quyền sở hữu
                      </option>
                      <option value="CREATIVE_WORK">Tác phẩm gốc</option>
                      <option value="OTHER">Tài liệu khác</option>
                    </select>
                  </div>
                  <div className="sm:col-span-2">
                    <FileUploader
                      disabled={attach.isPending}
                      label="Bằng chứng hồ sơ"
                      onComplete={(asset) => attach.mutate(asset)}
                      purpose="DOSSIER_EVIDENCE"
                    />
                  </div>
                </div>
              ) : null}
              {attach.error ? (
                <p
                  className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800"
                  role="alert"
                >
                  Tệp đã tải lên nhưng chưa gắn được vào hồ sơ. Vui lòng thử
                  lại.
                </p>
              ) : null}
              <div className="space-y-3">
                {dossier.evidences.length ? (
                  dossier.evidences.map((evidence) => (
                    <EvidenceItem
                      canEdit={dossier.canEdit}
                      evidence={evidence}
                      key={evidence.id}
                      onRemove={(id) => remove.mutate(id)}
                    />
                  ))
                ) : (
                  <div className="rounded-2xl border border-dashed border-neutral-300 px-5 py-10 text-center">
                    <Fingerprint
                      aria-hidden="true"
                      className="mx-auto size-7 text-neutral-400"
                    />
                    <p className="mt-3 font-bold">Chưa có bằng chứng</p>
                    <p className="mt-1 text-sm text-neutral-500">
                      Hồ sơ cần ít nhất một tệp đã xác minh để có thể nộp.
                    </p>
                  </div>
                )}
              </div>
            </section>
          ) : null}

          {step === "review" ? (
            <section className="space-y-6">
              <div>
                <h2 className="text-xl font-bold tracking-tight">
                  Kiểm tra & nộp
                </h2>
                <p className="mt-1 text-sm leading-6 text-neutral-500">
                  Kiểm tra lại thông tin và tài liệu trước khi gửi TMI xem xét.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="flex items-start gap-3 rounded-xl border border-neutral-200 p-4">
                  <CheckCircle2
                    aria-hidden="true"
                    className="mt-0.5 size-5 text-emerald-600"
                  />
                  <div>
                    <p className="text-sm font-bold">Thông tin hồ sơ</p>
                    <p className="mt-1 text-xs text-neutral-500">
                      Tên và danh mục hợp lệ
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-xl border border-neutral-200 p-4">
                  {dossier.evidences.length ? (
                    <CheckCircle2
                      aria-hidden="true"
                      className="mt-0.5 size-5 text-emerald-600"
                    />
                  ) : (
                    <CircleAlert
                      aria-hidden="true"
                      className="mt-0.5 size-5 text-amber-600"
                    />
                  )}
                  <div>
                    <p className="text-sm font-bold">Bằng chứng xác minh</p>
                    <p className="mt-1 text-xs text-neutral-500">
                      {dossier.evidences.length} tệp sẵn sàng
                    </p>
                  </div>
                </div>
              </div>
              {dossier.evidences.map((evidence) => (
                <EvidenceItem
                  canEdit={false}
                  evidence={evidence}
                  key={evidence.id}
                  onRemove={() => undefined}
                />
              ))}
              {dossier.canEdit ? (
                <div className="rounded-2xl border border-primary-200 bg-primary-50 p-5">
                  <div className="flex items-start gap-3">
                    <BadgeCheck
                      aria-hidden="true"
                      className="mt-0.5 size-5 text-primary-700"
                    />
                    <div>
                      <p className="font-bold text-primary-950">
                        Xác nhận nộp hồ sơ
                      </p>
                      <p className="mt-1 text-sm leading-6 text-primary-900/70">
                        Sau khi nộp, bạn không thể sửa phiên bản này trừ khi có
                        yêu cầu bổ sung.
                      </p>
                    </div>
                  </div>
                  <Button
                    className="mt-5 w-full sm:w-auto"
                    disabled={!isComplete || submit.isPending}
                    onClick={() => submit.mutate()}
                  >
                    <Send aria-hidden="true" className="size-4" />
                    {submit.isPending
                      ? "Đang tạo phiên bản…"
                      : dossier.status === "NEEDS_SUPPLEMENT"
                        ? "Nộp lại hồ sơ"
                        : "Nộp hồ sơ"}
                  </Button>
                </div>
              ) : null}
              {submit.error ? (
                <p
                  className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800"
                  role="alert"
                >
                  Chưa thể nộp hồ sơ. Hãy kiểm tra lại checklist và trạng thái
                  tệp.
                </p>
              ) : null}
              <div className="grid min-w-0 gap-5 lg:grid-cols-2">
                <div className="min-w-0">
                  <h3 className="font-bold">Phiên bản</h3>
                  <div className="mt-3 space-y-2">
                    {versions.data?.length ? (
                      versions.data.map((version) => (
                        <div
                          className="min-w-0 overflow-hidden rounded-xl border border-neutral-200 p-4"
                          key={version.id}
                        >
                          <p className="text-sm font-bold">
                            Phiên bản {version.versionNo}
                          </p>
                          <p className="mt-1 text-xs text-neutral-500">
                            Đã gửi{" "}
                            {new Date(version.submittedAt).toLocaleString(
                              "vi-VN",
                            )}
                          </p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-neutral-500">
                        Chưa có phiên bản đã nộp.
                      </p>
                    )}
                  </div>
                </div>
                <div className="min-w-0">
                  <h3 className="font-bold">Dòng thời gian</h3>
                  <div className="mt-3 space-y-2">
                    {timeline.data?.length ? (
                      timeline.data.map((item) => (
                        <div
                          className="flex gap-3 rounded-xl border border-neutral-200 p-4"
                          key={item.id}
                        >
                          <span className="mt-1 size-2 rounded-full bg-primary-600" />
                          <div>
                            <p className="text-sm font-bold">
                              {dossierStatusLabel(item.toStatus)}
                            </p>
                            <p className="mt-1 text-xs text-neutral-500">
                              {new Date(item.createdAt).toLocaleString("vi-VN")}
                            </p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-neutral-500">
                        Chưa có thay đổi trạng thái.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}
