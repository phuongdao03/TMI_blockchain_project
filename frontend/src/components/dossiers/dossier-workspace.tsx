"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  CheckCircle2,
  CircleAlert,
  FileCheck2,
  FileText,
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
import { DossierClaimsEditor } from "@/components/dossiers/dossier-claims-editor";
import { SupplementRequestsPanel } from "@/components/supplements/supplement-requests-panel";
import { FileUploader } from "@/components/media/file-uploader";
import { DossierPaymentAction } from "@/components/payments/dossier-payment-action";
import { PrivateDocumentVerification } from "@/components/documents/private-document-verification";
import { Button } from "@/components/ui/button";
import { dossierApi } from "@/lib/api/client";
import { displayCnsDossierCode } from "@/lib/brand/identifiers";
import type {
  DossierDetail,
  DossierDocumentRule,
  DossierEvidence,
  DossierStatus,
  MediaAsset,
} from "@/lib/api/types";
import { dossierKeys } from "@/lib/dossiers/query-keys";
import { cn } from "@/lib/utils";
import { useAuthUser } from "@/lib/auth/user-context";
import { DossierPromotionOptions } from "./dossier-promotion-options";

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
    label: "Tài liệu",
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
    outcome: "Tinh Hoa Việt đã nhận hồ sơ.",
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
    next: "Chờ Tinh Hoa Việt chuẩn bị bằng xác lập.",
  },
  ANCHOR_PENDING: {
    outcome: "Bằng xác lập đang được chuẩn bị.",
    next: "Theo dõi thông báo phát hành.",
  },
  ANCHORED: {
    outcome: "Bằng xác lập đã sẵn sàng để phát hành.",
    next: "Chờ thông báo tải bằng xác lập.",
  },
  CERTIFICATE_ISSUED: {
    outcome: "Bằng xác lập đã được phát hành.",
    next: "Mở danh sách bằng xác lập để tải xuống.",
  },
  PUBLISHED: {
    outcome: "Bằng xác lập đã được công bố.",
    next: "Tải bằng xác lập hoặc chia sẻ đường dẫn kiểm tra.",
  },
  REVOKED: {
    outcome: "Bằng xác lập không còn hiệu lực.",
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

function evidenceScopeLabel(
  scope: DossierEvidence["accessScope"] | null | undefined,
): string {
  return (
    {
      PRIVATE: "Chỉ chủ hồ sơ",
      INTERNAL: "Chỉ người xử lý",
      PUBLIC_PREVIEW: "Có thể dùng cho bản xem trước",
      PUBLIC: "Được công bố khi hồ sơ hợp lệ",
    }[scope ?? "INTERNAL"] ?? "Chỉ người xử lý"
  );
}

function ruleProgress(
  rule: DossierDocumentRule,
  evidences: DossierEvidence[],
): number {
  return evidences.filter((evidence) => evidence.evidenceRole === rule.key)
    .length;
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
    <article className="grid gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center">
      <span className="grid size-10 place-items-center rounded-full bg-emerald-50 text-emerald-700">
        <FileCheck2 aria-hidden="true" className="size-5" />
      </span>
      <div className="min-w-0">
        <h3 className="truncate text-sm font-bold text-neutral-950">
          {evidence.title}
        </h3>
        <p className="mt-1 text-xs text-neutral-500">
          {evidence.mimeType} · {formatBytes(evidence.bytes)} KB
        </p>
        <p className="mt-1 text-xs font-medium text-neutral-500">
          {evidenceScopeLabel(evidence.accessScope)}
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

function InformationStep({
  dossier,
  onUnsavedChange,
}: {
  dossier: DossierDetail;
  onUnsavedChange: (unsaved: boolean) => void;
}) {
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
    onSuccess: (saved, submitted) => {
      queryClient.setQueryData(dossierKeys.detail(dossier.id), {
        ...dossier,
        ...saved,
        evidences: dossier.evidences,
      });
      const latest = form.getValues();
      if (
        latest.title === submitted.title &&
        latest.summary === submitted.summary &&
        latest.visibility === submitted.visibility
      ) {
        form.reset({
          title: saved.title,
          summary: saved.summary ?? "",
          visibility: saved.visibility,
        });
      }
    },
  });
  const save = update.mutate;

  useEffect(() => {
    onUnsavedChange(
      dossier.canEdit && (form.formState.isDirty || update.isPending),
    );
  }, [
    dossier.canEdit,
    form.formState.isDirty,
    onUnsavedChange,
    update.isPending,
  ]);

  useEffect(() => {
    if (
      !dossier.canEdit ||
      !form.formState.isDirty ||
      update.isPending ||
      update.isError
    )
      return;
    const parsed = infoSchema.safeParse(values);
    if (!parsed.success) return;
    const timeout = window.setTimeout(() => save(parsed.data), 700);
    return () => window.clearTimeout(timeout);
  }, [
    dossier.canEdit,
    form.formState.isDirty,
    save,
    update.isError,
    update.isPending,
    values,
  ]);

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
          className="dossier-autosave-status inline-flex min-h-8 items-center gap-2 rounded-full px-3 text-xs font-bold"
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
          {update.isPending
            ? "Đang lưu…"
            : form.formState.isDirty
              ? "Chưa lưu"
              : "Đã lưu"}
        </span>
      </div>
      <div>
        <label className="text-sm font-bold" htmlFor="workspace-title">
          Tên hồ sơ
        </label>
        <input
          className="mt-2 min-h-12 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm text-[var(--theme-text)] outline-none focus:border-primary-500 focus:ring-4 focus:ring-primary-100 disabled:bg-[var(--theme-elevated)] disabled:text-[var(--theme-muted)]"
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
          className="mt-2 min-h-40 w-full resize-y rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-3 text-sm leading-6 text-[var(--theme-text)] outline-none focus:border-primary-500 focus:ring-4 focus:ring-primary-100 disabled:bg-[var(--theme-elevated)] disabled:text-[var(--theme-muted)]"
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
          className="mt-2 min-h-12 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm text-[var(--theme-text)] outline-none focus:border-primary-500 focus:ring-4 focus:ring-primary-100 disabled:bg-[var(--theme-elevated)]"
          disabled={!dossier.canEdit}
          id="workspace-visibility"
          {...form.register("visibility")}
        >
          <option value="PRIVATE">Riêng tư</option>
          <option value="UNLISTED">Không niêm yết</option>
          <option value="PUBLIC">Công khai sau cấp bằng xác lập</option>
        </select>
      </div>
      {update.error ? (
        <div
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800"
          role="alert"
        >
          <p>Tự động lưu chưa thành công. Dữ liệu vẫn còn trên biểu mẫu.</p>
          <Button
            className="mt-3"
            onClick={() =>
              void form.handleSubmit((next) => update.mutate(next))()
            }
            type="button"
            variant="outline"
          >
            Thử lưu lại
          </Button>
        </div>
      ) : null}
    </section>
  );
}

export function DossierWorkspace({
  dossierId,
  justCreated = false,
}: {
  dossierId: string;
  justCreated?: boolean;
}) {
  const user = useAuthUser();
  const [step, setStep] = useState<Step>(
    justCreated ? "evidence" : "information",
  );
  const [evidenceTitle, setEvidenceTitle] = useState("");
  const [evidenceType, setEvidenceType] = useState("OWNERSHIP_DOCUMENT");
  const [queueLocked, setQueueLocked] = useState(false);
  const [informationUnsaved, setInformationUnsaved] = useState(false);
  const [claimsUnsaved, setClaimsUnsaved] = useState(false);
  const [supplementsOpen, setSupplementsOpen] = useState(false);
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
  const documentRules = detail.data?.documentRules ?? [];
  const submissionFee = useQuery({
    queryKey: ["submission-fee", dossierId],
    queryFn: () => dossierApi.submissionFee(dossierId),
    enabled: Boolean(
      detail.data?.submissionFeeRequired && !detail.data?.submissionFeePaidAt,
    ),
    retry: false,
  });
  const selectedRule =
    documentRules.find((rule) => rule.key === evidenceType) ??
    documentRules.at(0);

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
    mutationFn: ({
      asset,
      displayOrder,
    }: {
      asset: MediaAsset;
      displayOrder: number;
    }) =>
      dossierApi.attachEvidence(dossierId, {
        mediaAssetId: asset.id,
        evidenceType: selectedRule?.documentType ?? evidenceType,
        evidenceRole: selectedRule?.key,
        title:
          evidenceTitle.trim() || selectedRule?.label || "Tài liệu chứng minh",
        displayOrder,
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
  const submissionComplete =
    submit.isSuccess && dossier.status !== "NEEDS_SUPPLEMENT";
  const supplementRequest = timeline.data
    ?.filter(
      (item) => item.toStatus === "NEEDS_SUPPLEMENT" && item.note?.trim(),
    )
    .at(-1)
    ?.note?.trim();
  const missingRequiredRules = documentRules.filter(
    (rule) => rule.required && ruleProgress(rule, dossier.evidences) === 0,
  );
  const selectedRuleCount = selectedRule
    ? ruleProgress(selectedRule, dossier.evidences)
    : dossier.evidences.length;
  const selectedRuleAtCapacity = Boolean(
    selectedRule && selectedRuleCount >= selectedRule.maxCount,
  );
  const claimsReady = (dossier.claims ?? []).every(
    (claim) =>
      claim.statement.trim().length >= 20 &&
      claim.evidenceMediaIds.length > 0 &&
      claim.evidenceMediaIds.every((id) =>
        dossier.evidences.some((evidence) => evidence.mediaAssetId === id),
      ),
  );
  const isComplete =
    claimsReady &&
    dossier.title.length >= 3 &&
    (documentRules.length
      ? missingRequiredRules.length === 0
      : dossier.evidences.length > 0);
  const informationReady = dossier.title.length >= 3;
  const evidenceReady = documentRules.length
    ? missingRequiredRules.length === 0
    : dossier.evidences.length > 0;
  const completedPreparationSteps = [informationReady, evidenceReady].filter(
    Boolean,
  ).length;
  const nextPreparationStep: Step = !informationReady
    ? "information"
    : !evidenceReady || !claimsReady
      ? "evidence"
      : "review";
  return (
    <div className="dossier-workspace mx-auto max-w-7xl space-y-6">
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
              {displayCnsDossierCode(dossier.code)}
            </span>
          </div>
          <h1 className="mt-3 break-words text-2xl font-semibold tracking-[-0.025em] text-neutral-950 sm:text-4xl">
            {dossier.title}
          </h1>
        </div>
        <p className="rounded-full border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-2 text-xs font-bold text-[var(--theme-muted)]">
          Phiên bản: {dossier.currentVersionNo || "Chưa nộp"}
        </p>
      </div>

      {justCreated && dossier.status === "DRAFT" ? (
        <p
          className="dossier-created-note text-sm text-[var(--theme-muted)]"
          role="status"
        >
          Đã lưu bản nháp. Thêm tài liệu cần thiết rồi kiểm tra trước khi gửi.
        </p>
      ) : null}

      {submissionComplete && submit.data ? (
        <section
          className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-950 sm:p-6"
          role="status"
        >
          <h2 className="text-xl font-bold">Hồ sơ đã được gửi thành công</h2>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-emerald-800">Mã hồ sơ</dt>
              <dd className="mt-1 font-bold">
                {displayCnsDossierCode(submit.data.dossier.code)}
              </dd>
            </div>
            <div>
              <dt className="text-emerald-800">Thời gian gửi</dt>
              <dd className="mt-1 font-bold">
                {new Date(submit.data.version.submittedAt).toLocaleString(
                  "vi-VN",
                )}
              </dd>
            </div>
            <div>
              <dt className="text-emerald-800">Trạng thái</dt>
              <dd className="mt-1 font-bold">
                {dossierStatusLabel(submit.data.dossier.status)}
              </dd>
            </div>
          </dl>
          <p className="mt-4 text-sm font-medium">
            {submit.data.dossier.status === "PAYMENT_PENDING"
              ? "Bước tiếp theo: thanh toán phí nộp để hồ sơ được tiếp nhận thẩm định."
              : "Bước tiếp theo: Tinh Hoa Việt kiểm tra hồ sơ của bạn."}
          </p>
          <ol
            aria-label="Các bước sau khi nộp"
            className="mt-4 grid gap-3 text-sm sm:grid-cols-3"
          >
            <li className="rounded-xl bg-white/60 p-3">
              <strong className="block">1. Đã tiếp nhận</strong>
              <span className="mt-1 block">
                Hồ sơ đã có mã để bạn theo dõi.
              </span>
            </li>
            <li className="rounded-xl bg-white/60 p-3">
              <strong className="block">
                {submit.data.dossier.status === "PAYMENT_PENDING"
                  ? "2. Thanh toán phí nộp"
                  : "2. Kiểm duyệt hồ sơ"}
              </strong>
              <span className="mt-1 block">
                {submit.data.dossier.status === "PAYMENT_PENDING"
                  ? "Xem khoản phí bên dưới và xác nhận thanh toán bằng ví."
                  : "Tinh Hoa Việt đối chiếu thông tin và tài liệu."}
              </span>
            </li>
            <li className="rounded-xl bg-white/60 p-3">
              <strong className="block">3. Thông báo kết quả</strong>
              <span className="mt-1 block">
                Xem yêu cầu bổ sung hoặc kết quả khi trạng thái đổi.
              </span>
            </li>
          </ol>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              className="inline-flex min-h-11 items-center rounded-xl bg-emerald-800 px-4 text-sm font-bold text-white hover:bg-emerald-900"
              href="/dossiers"
            >
              Về hồ sơ của tôi
            </Link>
            <Link
              className="inline-flex min-h-11 items-center rounded-xl border border-emerald-700 px-4 text-sm font-bold text-emerald-900 hover:bg-emerald-100"
              href="/notifications"
            >
              Xem thông báo
            </Link>
          </div>
        </section>
      ) : null}

      {!(justCreated && dossier.status === "DRAFT") && (
        <section className="dossier-state-card">
          <div className="grid gap-5 py-5 lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-center">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
                Việc cần làm tiếp theo
              </p>
              <p className="mt-2 text-lg font-bold leading-7 text-neutral-950">
                {dossierGuidance[dossier.status].next}
              </p>
              {dossier.status === "NEEDS_SUPPLEMENT" ? (
                <p className="mt-3 whitespace-pre-wrap rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm font-medium text-amber-950">
                  {supplementRequest
                    ? `Nội dung cần bổ sung: ${supplementRequest}`
                    : "Chưa có nội dung yêu cầu cụ thể trong lịch sử hồ sơ. Vui lòng kiểm tra thông báo hoặc liên hệ hỗ trợ."}
                </p>
              ) : null}
              {dossier.canEdit && !submissionComplete ? (
                <Button
                  className="mt-4"
                  disabled={
                    (claimsUnsaved && nextPreparationStep !== "evidence") ||
                    (queueLocked && nextPreparationStep !== "evidence") ||
                    (step === "information" &&
                      informationUnsaved &&
                      nextPreparationStep !== "information")
                  }
                  onClick={() => setStep(nextPreparationStep)}
                  type="button"
                >
                  Tiếp tục hoàn thiện
                  <ArrowRight aria-hidden="true" className="size-4" />
                </Button>
              ) : null}
            </div>
            <div
              className={cn(
                "dossier-state-summary border-t border-[var(--theme-border)] pt-4 text-sm text-[var(--theme-text)] lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0",
                dossier.canEdit && "hidden lg:block",
              )}
            >
              <p className="font-bold text-neutral-950">
                {dossierStatusLabel(dossier.status)}
              </p>
              <p className="mt-1 leading-6 text-neutral-600">
                {dossierGuidance[dossier.status].outcome}
              </p>
              {dossier.canEdit ? (
                <p className="mt-3 border-t border-primary-100 pt-3 text-xs font-semibold text-primary-800">
                  Đã xong {completedPreparationSteps}/2 phần chuẩn bị
                </p>
              ) : null}
            </div>
          </div>
        </section>
      )}

      {!dossier.canEdit ? (
        <section className="dossier-readonly-notice flex items-start gap-3 rounded-2xl p-4 text-sm">
          <LockKeyhole aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-bold">Hồ sơ đã nộp và đang ở chế độ chỉ đọc.</p>
            <p className="mt-1 leading-6 text-blue-800">
              Bạn vẫn có thể xem phiên bản và lịch sử. Chỉnh sửa chỉ mở lại khi
              hồ sơ được yêu cầu bổ sung.
            </p>
          </div>
        </section>
      ) : null}

      <DossierPaymentAction
        dossierId={dossier.id}
        dossierStatus={dossier.status}
        submissionFeeRequired={dossier.submissionFeeRequired}
        submissionFeePaidAt={dossier.submissionFeePaidAt}
      />
      {dossier.currentVersionNo > 0 ? (
        <SupplementRequestsPanel
          dossierId={dossier.id}
          mode="applicant"
          canRespond={dossier.status === "NEEDS_SUPPLEMENT"}
          onOpenChange={setSupplementsOpen}
        />
      ) : null}

      <div className="space-y-4">
        <div className={step === "information" ? "hidden" : undefined}>
          <DossierClaimsEditor
            key={`${dossier.id}-${dossier.status}`}
            dossierId={dossier.id}
            initialClaims={dossier.claims}
            initialRevision={dossier.claimsRevision}
            criteria={dossier.claimCriteria ?? []}
            evidences={dossier.evidences}
            readOnly={!dossier.canEdit || step === "review"}
            onSaved={() => void refresh()}
            onUnsavedChange={setClaimsUnsaved}
          />
        </div>
        <nav
          aria-label="Các bước hoàn thiện hồ sơ"
          className="grid gap-2 sm:grid-cols-3"
          id="dossier-steps"
        >
          {steps.map((item, index) => {
            const Icon = item.icon;
            const active = item.id === step;
            return (
              <button
                aria-current={active ? "step" : undefined}
                disabled={
                  (claimsUnsaved && item.id !== "evidence") ||
                  (queueLocked && item.id !== "evidence") ||
                  (step === "information" &&
                    informationUnsaved &&
                    item.id !== "information")
                }
                className={cn(
                  "flex min-h-12 min-w-0 w-full items-center gap-2 rounded-xl border px-3 py-2 text-left transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-16 sm:gap-3 sm:px-4 sm:py-3",
                  active
                    ? "border-primary-600 bg-primary-50 text-primary-900 dark:bg-primary-950/40 dark:text-primary-100"
                    : "border-[var(--theme-border)] bg-[var(--theme-surface)] text-[var(--theme-muted)] hover:bg-[var(--theme-elevated)]",
                )}
                key={item.id}
                onClick={() => setStep(item.id)}
                type="button"
              >
                <span
                  className={cn(
                    "grid size-8 shrink-0 place-items-center rounded-full",
                    active
                      ? "bg-primary-600 text-white"
                      : "bg-[var(--theme-elevated)] text-[var(--theme-muted)]",
                  )}
                >
                  <Icon aria-hidden="true" className="size-4" />
                </span>
                <span>
                  <span className="block text-xs font-bold sm:text-sm">
                    {index + 1}. {item.label}
                  </span>
                  <span className="mt-0.5 hidden text-xs opacity-70 sm:block">
                    {item.description}
                  </span>
                </span>
              </button>
            );
          })}
        </nav>

        <div className="min-w-0 bg-[var(--theme-surface)] px-1 py-4 text-[var(--theme-text)] sm:px-3 sm:py-5 lg:px-5 lg:py-6">
          {step === "information" ? (
            <InformationStep
              dossier={dossier}
              onUnsavedChange={setInformationUnsaved}
            />
          ) : null}

          {step === "evidence" ? (
            <section className="dossier-evidence-step space-y-6">
              <div>
                <h2 className="text-xl font-bold tracking-tight">
                  Tài liệu cho hồ sơ của bạn
                </h2>
                <p className="mt-1 text-sm leading-6 text-neutral-500">
                  Chọn loại tài liệu và tệp cần gửi. Tệp đã thêm sẽ hiện bên
                  dưới.
                </p>
              </div>
              {dossier.canEdit && !submissionComplete ? (
                <div className="space-y-5 rounded-2xl bg-[var(--theme-elevated)] p-4 sm:p-5">
                  {documentRules.length > 0 ? (
                    <fieldset className="space-y-3">
                      <legend className="text-sm font-bold">
                        Loại tài liệu
                      </legend>
                      <select
                        aria-label="Loại tài liệu cần thêm"
                        className="mt-2 min-h-12 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm font-semibold text-[var(--theme-text)] sm:hidden"
                        disabled={queueLocked || attach.isPending}
                        onChange={(event) => {
                          setEvidenceType(event.target.value);
                          setEvidenceTitle("");
                        }}
                        value={selectedRule?.key ?? evidenceType}
                      >
                        {documentRules.map((rule) => (
                          <option key={rule.key} value={rule.key}>
                            {rule.label} ·{" "}
                            {rule.required ? "Bắt buộc" : "Tùy chọn"} ·{" "}
                            {ruleProgress(rule, dossier.evidences)}/
                            {rule.maxCount} tệp
                          </option>
                        ))}
                      </select>
                      <div className="hidden gap-2 sm:grid sm:grid-cols-2 xl:grid-cols-3">
                        {documentRules.map((rule) => {
                          const count = ruleProgress(rule, dossier.evidences);
                          const selected = selectedRule?.key === rule.key;
                          return (
                            <button
                              key={rule.key}
                              type="button"
                              aria-pressed={selected}
                              disabled={
                                (queueLocked && !selected) || attach.isPending
                              }
                              onClick={() => {
                                setEvidenceType(rule.key);
                                setEvidenceTitle("");
                              }}
                              className={cn(
                                "min-h-20 rounded-xl border px-4 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:cursor-not-allowed disabled:opacity-50",
                                selected
                                  ? "border-primary-600 bg-primary-50 text-primary-950"
                                  : "border-[var(--theme-border)] bg-[var(--theme-surface)] hover:bg-[var(--theme-elevated)]",
                              )}
                            >
                              <strong className="block text-sm">
                                {rule.label}
                              </strong>
                              <span className="mt-1 block text-xs text-[var(--theme-muted)]">
                                {rule.required ? "Bắt buộc" : "Tùy chọn"} ·{" "}
                                {count}/{rule.maxCount} tệp
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </fieldset>
                  ) : null}
                  {documentRules.length === 0 ? (
                    <div>
                      <label
                        className="text-sm font-bold"
                        htmlFor="evidence-type"
                      >
                        Loại tài liệu
                      </label>
                      <select
                        className="mt-2 min-h-12 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm font-semibold text-[var(--theme-text)]"
                        id="evidence-type"
                        onChange={(event) =>
                          setEvidenceType(event.target.value)
                        }
                        value={evidenceType}
                        disabled={queueLocked || attach.isPending}
                      >
                        <option value="OWNERSHIP_DOCUMENT">
                          Bằng chứng về quyền hoặc nguồn gốc
                        </option>
                        <option value="CREATIVE_WORK">
                          Nội dung hoặc đối tượng đề cử
                        </option>
                        <option value="OTHER">Tài liệu khác</option>
                      </select>
                    </div>
                  ) : null}
                  {queueLocked ? (
                    <p
                      className="text-xs font-medium text-primary-800"
                      role="status"
                    >
                      Hoàn tất hoặc xóa tệp đang chọn trước khi đổi loại tài
                      liệu.
                    </p>
                  ) : null}
                  {selectedRule ? (
                    <p className="rounded-lg bg-[var(--theme-surface)] px-3 py-2 text-xs leading-5 text-[var(--theme-muted)]">
                      {selectedRule.required
                        ? "Cần có để nộp hồ sơ"
                        : "Không bắt buộc"}{" "}
                      · {evidenceScopeLabel(selectedRule.defaultVisibility)}.
                    </p>
                  ) : null}
                  <details className="rounded-xl bg-[var(--theme-surface)] p-3 sm:p-4">
                    <summary className="cursor-pointer text-sm font-semibold">
                      Đặt tên hiển thị cho tài liệu (tùy chọn)
                    </summary>
                    <div className="mt-3">
                      <label
                        className="text-sm font-bold"
                        htmlFor="evidence-title"
                      >
                        Tên tài liệu
                      </label>
                      <input
                        className="mt-2 min-h-12 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm text-[var(--theme-text)]"
                        id="evidence-title"
                        disabled={queueLocked || attach.isPending}
                        onChange={(event) =>
                          setEvidenceTitle(event.target.value)
                        }
                        placeholder={
                          selectedRule?.label ?? "Ví dụ: Video tác phẩm gốc"
                        }
                        value={evidenceTitle}
                      />
                      <p className="mt-1 text-xs leading-5 text-[var(--theme-muted)]">
                        Có thể để trống; hệ thống sẽ dùng tên loại tài liệu.
                      </p>
                    </div>
                  </details>
                  <div>
                    <FileUploader
                      compact
                      key={selectedRule?.key ?? evidenceType}
                      constraints={
                        selectedRule
                          ? {
                              allowedMimeTypes: selectedRule.allowedMimeTypes,
                              maxBytes: selectedRule.maxBytes,
                            }
                          : undefined
                      }
                      disabled={attach.isPending || selectedRuleAtCapacity}
                      label={selectedRule?.label ?? "Bằng chứng hồ sơ"}
                      maxFiles={
                        selectedRule
                          ? selectedRule.maxCount - selectedRuleCount
                          : undefined
                      }
                      multiple
                      onQueueChange={setQueueLocked}
                      onComplete={async (asset, index) => {
                        await attach.mutateAsync({
                          asset,
                          displayOrder: dossier.evidences.length + index,
                        });
                      }}
                      purpose="DOSSIER_EVIDENCE"
                    />
                    {selectedRuleAtCapacity ? (
                      <p
                        className="mt-3 text-sm font-medium text-amber-700"
                        role="status"
                      >
                        Đã đạt số lượng tối đa cho loại tài liệu này.
                      </p>
                    ) : null}
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
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-bold text-[var(--theme-text)]">
                    Tệp đã thêm
                  </h3>
                  <span className="text-xs font-semibold text-neutral-500">
                    {dossier.evidences.length} tệp
                  </span>
                </div>
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
                  <div className="flex items-start gap-3 rounded-xl border border-dashed border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4">
                    <span className="grid size-9 shrink-0 place-items-center text-[var(--theme-muted)]">
                      <FileCheck2 aria-hidden="true" className="size-4" />
                    </span>
                    <div>
                      <p className="text-sm font-bold">Chưa có tài liệu</p>
                      <p className="mt-1 text-xs leading-5 text-neutral-500">
                        Chọn tệp ở phía trên; tệp hợp lệ sẽ xuất hiện tại đây.
                      </p>
                    </div>
                  </div>
                )}
              </div>
              <div className="flex flex-wrap justify-between gap-3 pt-2">
                <Button
                  variant="outline"
                  disabled={queueLocked}
                  onClick={() => setStep("information")}
                >
                  Quay lại thông tin
                </Button>
                <Button
                  disabled={queueLocked}
                  onClick={() => setStep("review")}
                >
                  Tiếp tục kiểm tra →
                </Button>
              </div>
            </section>
          ) : null}

          {step === "review" ? (
            <section className="space-y-6">
              {!claimsReady ? (
                <p
                  className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"
                  role="alert"
                >
                  Nhận định đã lưu còn thiếu nội dung hoặc minh chứng. Quay lại
                  bước Tài liệu để hoàn thiện trước khi nộp.
                </p>
              ) : null}
              <div>
                <h2 className="text-xl font-bold tracking-tight">
                  Kiểm tra & nộp
                </h2>
                <p className="mt-1 text-sm leading-6 text-neutral-500">
                  Kiểm tra lại thông tin và tài liệu trước khi gửi Tinh Hoa Việt
                  xem xét.
                </p>
              </div>
              {missingRequiredRules.length ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                  <p className="font-bold">Cần bổ sung trước khi nộp</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {missingRequiredRules.map((rule) => (
                      <li key={rule.key}>{rule.label}</li>
                    ))}
                  </ul>
                  <Button
                    className="mt-3"
                    variant="outline"
                    onClick={() => setStep("evidence")}
                  >
                    Bổ sung tài liệu
                  </Button>
                </div>
              ) : null}
              <div
                aria-label="Kiểm tra trước khi nộp"
                className="grid gap-3 sm:grid-cols-2"
              >
                <div className="flex items-start gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4">
                  <CheckCircle2
                    aria-hidden="true"
                    className="mt-0.5 size-5 text-emerald-600"
                  />
                  <div>
                    <p className="text-sm font-bold">Thông tin hồ sơ</p>
                    <p className="mt-1 text-xs text-neutral-500">
                      Tên và danh mục hợp lệ
                    </p>
                    <p className="mt-2 text-sm font-semibold break-words">
                      {dossier.title}
                    </p>
                    <Button
                      className="mt-2 px-0 text-[var(--theme-accent)]"
                      variant="ghost"
                      onClick={() => setStep("information")}
                    >
                      Xem / sửa thông tin
                    </Button>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4">
                  {isComplete ? (
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
                      {documentRules.length
                        ? evidenceReady
                          ? "Đã đáp ứng các tài liệu bắt buộc"
                          : "Chưa đáp ứng các tài liệu bắt buộc"
                        : `${dossier.evidences.length} tệp sẵn sàng`}
                    </p>
                    <Button
                      className="mt-2 px-0 text-[var(--theme-accent)]"
                      variant="ghost"
                      onClick={() => setStep("evidence")}
                    >
                      Xem / sửa tài liệu
                    </Button>
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
              {dossier.canEdit && !submissionComplete ? (
                <div>
                  <div className="flex items-start gap-3">
                    <BadgeCheck
                      aria-hidden="true"
                      className="mt-0.5 size-5 text-[var(--theme-accent)]"
                    />
                    <div>
                      <p className="font-bold text-[var(--theme-text)]">
                        Xác nhận nộp hồ sơ
                      </p>
                      <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
                        Sau khi nộp, bạn không thể sửa phiên bản này trừ khi có
                        yêu cầu bổ sung.
                      </p>
                    </div>
                  </div>
                  <Button
                    className="mt-5 w-full sm:w-auto"
                    disabled={
                      !isComplete ||
                      claimsUnsaved ||
                      supplementsOpen ||
                      submit.isPending ||
                      submissionComplete ||
                      Boolean(
                        dossier.submissionFeeRequired &&
                          !dossier.submissionFeePaidAt &&
                          !submissionFee.data,
                      )
                    }
                    onClick={() => submit.mutate()}
                  >
                    <Send aria-hidden="true" className="size-4" />
                    {submit.isPending
                      ? "Đang tạo phiên bản…"
                      : dossier.status === "NEEDS_SUPPLEMENT"
                        ? "Nộp lại hồ sơ"
                        : "Nộp hồ sơ"}
                  </Button>
                  {dossier.submissionFeeRequired &&
                  !dossier.submissionFeePaidAt ? (
                    <div
                      className="mt-4 border-t border-[var(--theme-border)] pt-4 text-sm"
                      role="status"
                    >
                      {submissionFee.data ? (
                        <>
                          <p className="font-bold">
                            Phí nộp hồ sơ:{" "}
                            {new Intl.NumberFormat("vi-VN").format(
                              submissionFee.data.amountMinor,
                            )}{" "}
                            {submissionFee.data.currency}
                          </p>
                          <p className="mt-2">
                            Thanh toán bằng ví sau khi nộp, trước khi thẩm định.
                            Bổ sung hoặc phê duyệt không thu lại khoản phí này.
                            Việc nộp phí không bảo đảm hồ sơ được phê duyệt.
                          </p>
                        </>
                      ) : submissionFee.isError ? (
                        <>
                          <p>
                            Chưa tải được phí nộp. Dữ liệu hồ sơ vẫn được giữ.
                          </p>
                          <button
                            type="button"
                            className="min-h-11 font-bold underline"
                            onClick={() => void submissionFee.refetch()}
                          >
                            Tải lại phí nộp
                          </button>
                        </>
                      ) : (
                        "Đang tải phí nộp hồ sơ…"
                      )}
                    </div>
                  ) : null}
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
                          className="min-w-0 overflow-hidden rounded-lg bg-[var(--theme-elevated)] p-3"
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
                          className="flex gap-3 rounded-lg bg-[var(--theme-elevated)] p-3"
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

      {user?.id === dossier.ownerUserId && user.roles.includes("USER") ? (
        <DossierPromotionOptions
          dossierId={dossier.id}
          status={dossier.status}
        />
      ) : null}
      {dossier.status !== "DRAFT" && (
        <div id="dossier-publication-progress" tabIndex={-1}>
          <DossierWorkflowTimeline
            history={timeline.data ?? []}
            status={dossier.status}
            submissionFeeRequired={dossier.submissionFeeRequired}
          />
        </div>
      )}
    </div>
  );
}
