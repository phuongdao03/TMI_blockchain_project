"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  FilePlus2,
  ListChecks,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm, useWatch } from "react-hook-form";
import { useRef, useState } from "react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { startNavigationFeedback } from "@/components/ui/navigation-loading";
import { ApiError, dossierApi } from "@/lib/api/client";
import { dossierKeys } from "@/lib/dossiers/query-keys";
import { useAuthUser } from "@/lib/auth/user-context";
import { useDossierPreparation } from "./use-dossier-preparation";
import { PreparationRecoveryNotice } from "./preparation-recovery-notice";

const schema = z.object({
  title: z.string().trim().min(3, "Tên hồ sơ cần ít nhất 3 ký tự.").max(255),
  summary: z.string().trim().max(10_000).optional(),
  visibility: z.enum(["PRIVATE", "UNLISTED", "PUBLIC"]),
});

type FormValues = z.infer<typeof schema>;

function stringFieldValue(value: unknown): string {
  return typeof value === "string" || typeof value === "number"
    ? String(value)
    : "";
}

function multiSelectFieldValue(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function hasRequiredValue(value: unknown): boolean {
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value === "boolean") return value;
  if (Array.isArray(value)) return value.length > 0;
  return value !== null && value !== undefined;
}

function displayFieldValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ") || "Chưa điền";
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value === "string" || typeof value === "number") {
    return String(value).trim() || "Chưa điền";
  }
  return "Chưa điền";
}

function displayFieldLabel(label: string | undefined, key: string): string {
  return label === "Tác giả sáng kiến" ? "Tác giả" : label || key;
}

function normalizeSearchText(value: string): string {
  return value
    .toLocaleLowerCase("vi")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replaceAll("đ", "d");
}

const mimeLabels: Record<string, string> = {
  "application/pdf": "PDF",
  "application/msword": "DOC",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
    "DOCX",
  "image/jpeg": "JPG",
  "image/png": "PNG",
  "image/webp": "WEBP",
  "video/mp4": "MP4",
  "audio/mpeg": "MP3",
};

export function DossierCreateForm() {
  const router = useRouter();
  const user = useAuthUser();
  const formRef = useRef<HTMLFormElement>(null);
  const preflightRef = useRef<HTMLElement>(null);
  const queryClient = useQueryClient();
  const [dossierTypeVersionId, setDossierTypeVersionId] = useState("");
  const [typeQuery, setTypeQuery] = useState("");
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [prepareStep, setPrepareStep] = useState<0 | 1 | 2 | 3>(0);
  const [stepError, setStepError] = useState("");
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "",
      summary: "",
      visibility: "PRIVATE",
    },
  });
  const dossierTypes = useQuery({
    queryKey: dossierKeys.types(),
    queryFn: dossierApi.listTypes,
  });
  const values = useWatch({ control: form.control });
  const title = values.title ?? "";
  const recovery = useDossierPreparation({
    userId: user?.id,
    value: {
      dossierTypeVersionId: dossierTypeVersionId || null,
      step: prepareStep,
      values: {
        title,
        summary: values.summary ?? "",
        visibility: values.visibility ?? "PRIVATE",
      },
      formData,
    },
    onRestore: (payload) => {
      form.reset(payload.values);
      setDossierTypeVersionId(payload.dossierTypeVersionId ?? "");
      setFormData(payload.formData);
      setPrepareStep(payload.step);
    },
  });
  const dossierType = dossierTypes.data?.find(
    (item) => item.currentVersion.id === dossierTypeVersionId,
  );
  const hasDossierTypes = (dossierTypes.data?.length ?? 0) > 0;
  const normalizedTypeQuery = normalizeSearchText(typeQuery.trim());
  const visibleDossierTypes = dossierTypes.data?.filter((item) =>
    normalizeSearchText(
      `${item.name} ${item.currentVersion.schema.description ?? ""}`,
    ).includes(normalizedTypeQuery),
  );
  const dossierTypeDescription = dossierType?.currentVersion.schema.description;
  const documentRules = dossierType?.currentVersion.schema.documentRules ?? [];
  const reviewRubric = dossierType?.currentVersion.schema.reviewRubric;
  const requiredFieldCount =
    dossierType?.currentVersion.schema.fields.filter((field) => field.required)
      .length ?? 0;
  const requiredFields =
    dossierType?.currentVersion.schema.fields.filter(
      (field) => field.required,
    ) ?? [];
  const requiredDocumentRules = documentRules.filter((rule) => rule.required);
  const primaryDocumentRule = documentRules.find(
    (rule) => rule.key === "PRIMARY",
  );
  const primaryFormats = Array.from(
    new Set(
      (primaryDocumentRule?.allowedMimeTypes ?? []).map(
        (mime) => mimeLabels[mime] ?? mime,
      ),
    ),
  );
  const hasTypeSpecificFields = Boolean(
    dossierType?.currentVersion.schema.fields.length,
  );
  const informationTotal = 1 + requiredFields.length;
  const informationComplete =
    (title.trim().length >= 3 ? 1 : 0) +
    requiredFields.filter((field) => hasRequiredValue(formData[field.key]))
      .length;
  const create = useMutation({
    mutationFn: dossierApi.create,
    onError: (failure) => {
      if (
        failure instanceof ApiError &&
        failure.code === "DOSSIER_PREPARATION_CONFLICT"
      )
        void recovery.checkConflict();
    },
    onSuccess: async (dossier) => {
      recovery.finish();
      await queryClient.invalidateQueries({ queryKey: dossierKeys.lists() });
      startNavigationFeedback();
      router.push(`/dossiers/${dossier.id}?created=1`);
    },
  });

  const submit = form.handleSubmit((values) => {
    if (
      !dossierType ||
      prepareStep !== 3 ||
      informationComplete !== informationTotal ||
      recovery.dirty ||
      recovery.saving ||
      recovery.conflict
    )
      return;
    create.mutate({
      categoryId: dossierType.categoryId,
      title: values.title,
      summary: values.summary || null,
      visibility: values.visibility,
      dossierTypeVersionId,
      formData,
      ...(recovery.revision ? { preparationRevision: recovery.revision } : {}),
    });
  });

  const reviewCoreInformation = async () => {
    const valid = await form.trigger();
    if (!valid) {
      setStepError("Kiểm tra lại tên hồ sơ trước khi tiếp tục.");
      return;
    }
    setStepError("");
    setPrepareStep(hasTypeSpecificFields ? 2 : 3);
  };

  const reviewAdditionalInformation = () => {
    const missing = requiredFields.find(
      (field) => !hasRequiredValue(formData[field.key]),
    );
    if (missing) {
      setStepError(
        `Vui lòng điền ${missing.label || missing.key} trước khi tiếp tục.`,
      );
      return;
    }
    if (!formRef.current?.reportValidity()) {
      setStepError(
        "Kiểm tra định dạng các trường thông tin trước khi tiếp tục.",
      );
      return;
    }
    setStepError("");
    setPrepareStep(3);
  };

  if (!recovery.ready)
    return (
      <section
        className="rounded-lg border border-[var(--theme-border)] p-5"
        role="status"
      >
        <p>{recovery.error || "Đang kiểm tra dữ liệu hồ sơ đang chuẩn bị…"}</p>
        {recovery.error ? (
          <button
            type="button"
            className="mt-3 min-h-11 font-bold underline"
            onClick={recovery.retryLoad}
          >
            Thử khôi phục lại
          </button>
        ) : null}
      </section>
    );

  return (
    <form
      className="dossier-create-form space-y-5 sm:space-y-6"
      onSubmit={submit}
      ref={formRef}
    >
      {user ? <PreparationRecoveryNotice recovery={recovery} /> : null}
      <nav aria-label="Các bước chuẩn bị hồ sơ nháp">
        <ol
          className={`dossier-journey grid grid-cols-2 gap-2 ${hasTypeSpecificFields ? "sm:grid-cols-4" : "dossier-journey--three sm:grid-cols-3"}`}
        >
          {(
            [
              [0, "01", "Chọn loại", "Chọn hồ sơ phù hợp"],
              [1, "02", "Cơ bản", "Tên và mô tả"],
              ...(hasTypeSpecificFields
                ? [[2, "03", "Theo loại", "Thông tin riêng"]]
                : []),
              [
                3,
                hasTypeSpecificFields ? "04" : "03",
                "Kiểm tra",
                "Lưu bản nháp",
              ],
            ] as Array<[number, string, string, string]>
          ).map(([step, number, label, note]) => (
            <li
              aria-current={step === prepareStep ? "step" : undefined}
              className={`dossier-journey__item flex min-h-11 items-center gap-2 rounded-lg px-3 py-2 text-left text-sm ${
                step === prepareStep
                  ? "dossier-journey__item--active bg-[var(--theme-elevated)] font-bold text-[var(--theme-text)]"
                  : "text-[var(--theme-muted)]"
              }`}
              key={number}
            >
              <span className="grid size-6 shrink-0 place-items-center rounded-full bg-[var(--theme-surface)] text-[11px] font-bold text-[var(--theme-accent)]">
                {number}
              </span>
              <strong className="text-xs sm:text-sm">{label}</strong>
              <span className="sr-only">{note}</span>
            </li>
          ))}
        </ol>
      </nav>
      <section className="space-y-5 bg-white py-3 sm:rounded-2xl sm:border sm:border-neutral-200 sm:p-6">
        <div className="flex items-start gap-3">
          <ShieldCheck
            aria-hidden="true"
            className="mt-0.5 hidden size-5 shrink-0 text-primary-700 sm:block"
          />
          <div>
            <h2 className="font-bold text-neutral-950">
              {dossierType?.name ?? "Chọn loại hồ sơ để bắt đầu"}
            </h2>
            <p className="mt-1 text-sm leading-6 text-neutral-500">
              {dossierTypeDescription ??
                "Chọn loại phù hợp để hệ thống hiển thị đúng thông tin và tài liệu cần chuẩn bị."}
            </p>
          </div>
        </div>
        {prepareStep === 0 ? (
          <fieldset aria-describedby="dossier-type-help">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <legend className="text-sm font-bold text-neutral-900">
                Loại hồ sơ
              </legend>
              {dossierTypes.data ? (
                <span className="text-xs font-medium text-neutral-500">
                  {dossierTypes.data.length} loại đang áp dụng
                </span>
              ) : null}
            </div>
            <p className="mt-1 text-sm text-neutral-500" id="dossier-type-help">
              Chọn một loại để nạp biểu mẫu đúng phiên bản.
            </p>
            {hasDossierTypes ? (
              <>
                <label
                  className="mt-4 block text-xs font-semibold text-neutral-600"
                  htmlFor="dossier-type-search"
                >
                  Tìm loại hồ sơ
                </label>
                <input
                  autoComplete="off"
                  className="mt-2 min-h-12 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]"
                  id="dossier-type-search"
                  onChange={(event) => setTypeQuery(event.target.value)}
                  placeholder="Ví dụ: di sản, tác phẩm…"
                  type="search"
                  value={typeQuery}
                />
                {typeQuery.trim() ? (
                  <div className="mt-2 text-xs text-neutral-600" role="status">
                    <p>{visibleDossierTypes?.length ?? 0} loại phù hợp</p>
                    {dossierType &&
                    !visibleDossierTypes?.some(
                      (item) => item.currentVersion.id === dossierTypeVersionId,
                    ) ? (
                      <p className="mt-1 font-semibold text-[var(--theme-text)]">
                        Đang chọn: {dossierType.name}
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </>
            ) : null}
            {dossierType && prepareStep === 0 ? (
              <section
                aria-labelledby="document-preflight-title"
                className="dossier-preflight rounded-xl bg-[var(--theme-elevated)] p-4 sm:p-5"
                ref={preflightRef}
              >
                <div className="flex items-start gap-3">
                  <span className="grid size-8 shrink-0 place-items-center text-primary-700">
                    <ListChecks aria-hidden="true" className="size-5" />
                  </span>
                  <div>
                    <h2 className="font-bold" id="document-preflight-title">
                      Khác biệt của loại hồ sơ này
                    </h2>
                    <p className="mt-1 text-sm leading-6 text-neutral-600">
                      {reviewRubric?.criteria.length
                        ? "Biểu mẫu và trọng tâm thẩm định hiển thị theo loại hồ sơ này."
                        : "Biểu mẫu của loại này xác định các thông tin cần khai; bằng chứng được bổ sung sau khi tạo bản nháp."}
                    </p>
                  </div>
                </div>

                <div
                  className={`mt-4 grid gap-3 ${reviewRubric?.criteria.length ? "sm:grid-cols-2" : ""}`}
                >
                  <section className="min-w-0 rounded-lg bg-[var(--theme-surface)] p-3">
                    <h3 className="text-sm font-bold">Thông tin cần khai</h3>
                    <p className="mt-1 text-xs text-neutral-600">
                      {requiredFieldCount} trường bắt buộc
                    </p>
                    {requiredFields.length ? (
                      <ul className="mt-2 space-y-1.5 text-sm" role="list">
                        {requiredFields.map((field) => (
                          <li
                            className="flex items-start gap-2"
                            key={field.key}
                          >
                            <Check
                              aria-hidden="true"
                              className="mt-0.5 size-4 shrink-0 text-primary-700"
                            />
                            <span>{field.label ?? field.key}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-sm text-neutral-600">
                        Không có trường riêng bắt buộc.
                      </p>
                    )}
                  </section>

                  {reviewRubric?.criteria.length ? (
                    <section className="min-w-0 rounded-lg bg-[var(--theme-surface)] p-3">
                      <h3 className="text-sm font-bold">Trọng tâm thẩm định</h3>
                      <ul className="mt-2 space-y-1.5 text-sm" role="list">
                        {reviewRubric.criteria.map((criterion) => (
                          <li
                            className="flex items-start gap-2"
                            key={criterion.key}
                          >
                            <ShieldCheck
                              aria-hidden="true"
                              className="mt-0.5 size-4 shrink-0 text-primary-700"
                            />
                            <span>{criterion.label}</span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  ) : null}
                </div>

                <div className="mt-3 flex flex-col gap-1 border-t border-[var(--theme-border)] pt-3 text-xs leading-5 text-neutral-600 sm:flex-row sm:justify-between sm:gap-4">
                  <p>
                    <strong className="text-[var(--theme-text)]">
                      Giấy tờ bắt buộc:
                    </strong>{" "}
                    {requiredDocumentRules.length
                      ? requiredDocumentRules
                          .map((rule) => rule.label ?? rule.documentType)
                          .join(", ")
                      : "Không bắt buộc theo nhóm giấy tờ."}
                  </p>
                  {primaryFormats.length ? (
                    <p>
                      <strong className="text-[var(--theme-text)]">
                        Tệp nội dung chính:
                      </strong>{" "}
                      {primaryFormats.join(", ")}
                    </p>
                  ) : null}
                </div>
                <p className="mt-2 text-xs leading-5 text-neutral-600">
                  Có thể tải bằng chứng ở bước tiếp theo; khi nộp hồ sơ cần ít
                  nhất một tệp đã xác minh.
                </p>
              </section>
            ) : null}
            <div className="mt-3 grid gap-2.5 sm:grid-cols-2 sm:gap-3">
              {visibleDossierTypes?.map((item) => {
                const selected =
                  item.currentVersion.id === dossierTypeVersionId;
                const description = item.currentVersion.schema.description;
                const itemRequiredCount =
                  item.currentVersion.schema.fields.filter(
                    (field) => field.required,
                  ).length;
                const itemCriterionCount =
                  item.currentVersion.schema.reviewRubric?.criteria.length ?? 0;
                return (
                  <label
                    className="dossier-type-option"
                    key={item.currentVersion.id}
                  >
                    <input
                      checked={selected}
                      className="sr-only"
                      name="dossier-type"
                      onChange={() => {
                        setDossierTypeVersionId(item.currentVersion.id);
                        setFormData({});
                        setStepError("");
                        if (window.matchMedia?.("(max-width: 639px)").matches) {
                          requestAnimationFrame(() =>
                            preflightRef.current?.scrollIntoView({
                              block: "start",
                              behavior: window.matchMedia(
                                "(prefers-reduced-motion: reduce)",
                              ).matches
                                ? "auto"
                                : "smooth",
                            }),
                          );
                        }
                      }}
                      type="radio"
                      value={item.currentVersion.id}
                    />
                    <span
                      className="dossier-type-option__indicator"
                      aria-hidden="true"
                    >
                      {selected ? <Check className="size-3.5" /> : null}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-bold text-neutral-950">
                        {item.name}
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-neutral-500">
                        {description ??
                          `Biểu mẫu phiên bản ${item.currentVersion.versionNo}`}
                      </span>
                      <span className="mt-2 block text-[0.6875rem] font-semibold text-[var(--theme-accent)]">
                        {itemRequiredCount} thông tin bắt buộc
                        {itemCriterionCount
                          ? ` · ${itemCriterionCount} tiêu chí thẩm định`
                          : ""}
                      </span>
                    </span>
                  </label>
                );
              })}
            </div>
            {hasDossierTypes && visibleDossierTypes?.length === 0 ? (
              <p className="mt-3 text-sm text-neutral-600" role="status">
                Không tìm thấy loại phù hợp. Hãy thử tên hoặc chủ đề khác.
              </p>
            ) : null}
            {dossierTypes.isError ? (
              <div
                className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4"
                role="alert"
              >
                <p className="text-sm font-medium text-red-800">
                  Chưa thể tải danh mục hồ sơ. Vui lòng kiểm tra kết nối và thử
                  lại.
                </p>
                <Button
                  disabled={dossierTypes.isFetching}
                  onClick={() => void dossierTypes.refetch()}
                  type="button"
                  variant="outline"
                >
                  <RefreshCw
                    aria-hidden="true"
                    className={`size-4 ${dossierTypes.isFetching ? "animate-spin" : ""}`}
                  />
                  {dossierTypes.isFetching ? "Đang tải lại…" : "Thử tải lại"}
                </Button>
              </div>
            ) : null}
            {dossierTypes.isLoading ? (
              <p className="mt-3 text-sm text-neutral-500">
                Đang tải danh mục hồ sơ…
              </p>
            ) : null}
            {dossierTypes.isSuccess && !hasDossierTypes ? (
              <p className="mt-3 text-sm text-neutral-500" role="status">
                Hiện chưa có loại hồ sơ đang mở. Vui lòng liên hệ bộ phận hỗ
                trợ.
              </p>
            ) : null}
          </fieldset>
        ) : null}

        {hasDossierTypes ? (
          <>
            {prepareStep === 1 ? (
              <>
                <div>
                  <label
                    className="dossier-required-label text-sm font-bold text-neutral-900"
                    htmlFor="dossier-title"
                  >
                    Tên tài sản hoặc tác phẩm
                  </label>
                  <input
                    aria-describedby="dossier-title-error"
                    className="mt-2 min-h-12 w-full rounded-xl border border-neutral-200 bg-white px-4 text-sm outline-none transition focus:border-primary-500 focus:ring-4 focus:ring-primary-100"
                    id="dossier-title"
                    placeholder="Ví dụ: Bộ sưu tập văn hóa Việt"
                    {...form.register("title")}
                    aria-required="true"
                  />
                  {form.formState.errors.title ? (
                    <p
                      className="mt-2 text-sm font-medium text-error"
                      id="dossier-title-error"
                      role="alert"
                    >
                      {form.formState.errors.title.message}
                    </p>
                  ) : null}
                </div>

                <div>
                  <label
                    className="text-sm font-bold text-neutral-900"
                    htmlFor="dossier-summary"
                  >
                    Mô tả ngắn
                  </label>
                  <textarea
                    className="mt-2 min-h-32 w-full resize-y rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm leading-6 outline-none transition focus:border-primary-500 focus:ring-4 focus:ring-primary-100"
                    id="dossier-summary"
                    placeholder="Nêu mục đích, nguồn gốc và phạm vi tài sản cần xác lập."
                    {...form.register("summary")}
                  />
                </div>

                <fieldset>
                  <legend className="text-sm font-bold text-neutral-900">
                    Chế độ hiển thị
                  </legend>
                  <div className="mt-2 grid gap-3 sm:grid-cols-3">
                    {[
                      [
                        "PRIVATE",
                        "Riêng tư",
                        "Chỉ bạn và người được cấp quyền xem",
                      ],
                      ["UNLISTED", "Không niêm yết", "Chỉ người có liên kết"],
                      [
                        "PUBLIC",
                        "Công khai",
                        "Có thể công bố sau cấp bằng xác lập",
                      ],
                    ].map(([value, label, description]) => (
                      <label className="dossier-visibility-option" key={value}>
                        <input
                          className="accent-primary-600"
                          type="radio"
                          value={value}
                          {...form.register("visibility")}
                        />
                        <span className="ml-2 text-sm font-bold">{label}</span>
                        <span className="mt-1 block pl-6 text-xs leading-5 text-neutral-500">
                          {description}
                        </span>
                      </label>
                    ))}
                  </div>
                </fieldset>
              </>
            ) : null}
            {prepareStep === 2 ? (
              <>
                <p className="text-sm leading-6 text-[var(--theme-muted)]">
                  Điền các mục có dấu *. Nội dung đã nhập được giữ khi bạn đổi
                  bước.
                </p>
                {dossierType?.currentVersion.schema.fields.map((field) => (
                  <div key={field.key}>
                    <label
                      className="text-sm font-bold text-neutral-900"
                      htmlFor={`field-${field.key}`}
                    >
                      {displayFieldLabel(field.label, field.key)}
                      {field.required ? " *" : ""}
                    </label>
                    {field.helpText ? (
                      <p className="mt-1 text-xs leading-5 text-neutral-500">
                        {field.helpText}
                      </p>
                    ) : null}
                    {field.type === "textarea" ? (
                      <textarea
                        className="mt-2 min-h-28 w-full resize-y rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm leading-6"
                        id={`field-${field.key}`}
                        onChange={(event) =>
                          setFormData((current) => ({
                            ...current,
                            [field.key]: event.target.value,
                          }))
                        }
                        placeholder={field.placeholder}
                        required={field.required}
                        value={stringFieldValue(formData[field.key])}
                      />
                    ) : field.type === "select" ? (
                      <select
                        className="mt-2 min-h-12 w-full rounded-xl border border-neutral-200 bg-white px-4 text-sm"
                        id={`field-${field.key}`}
                        onChange={(event) =>
                          setFormData((current) => ({
                            ...current,
                            [field.key]: event.target.value,
                          }))
                        }
                        required={field.required}
                        value={stringFieldValue(formData[field.key])}
                      >
                        <option value="">Chọn phương án</option>
                        {(field.options ?? []).map((option) => {
                          const value =
                            typeof option === "string" ? option : option.value;
                          const label =
                            typeof option === "string"
                              ? option
                              : (option.label ?? option.value);
                          return (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          );
                        })}
                      </select>
                    ) : field.type === "multiselect" ? (
                      <select
                        className="mt-2 min-h-28 w-full rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm"
                        id={`field-${field.key}`}
                        multiple
                        onChange={(event) =>
                          setFormData((current) => ({
                            ...current,
                            [field.key]: Array.from(
                              event.target.selectedOptions,
                              (option) => option.value,
                            ),
                          }))
                        }
                        required={field.required}
                        value={multiSelectFieldValue(formData[field.key])}
                      >
                        {(field.options ?? []).map((option) => {
                          const value =
                            typeof option === "string" ? option : option.value;
                          const label =
                            typeof option === "string"
                              ? option
                              : (option.label ?? option.value);
                          return (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          );
                        })}
                      </select>
                    ) : field.type === "radio" ? (
                      <fieldset className="mt-2 grid gap-2 sm:grid-cols-2">
                        <legend className="sr-only">
                          {displayFieldLabel(field.label, field.key)}
                        </legend>
                        {(field.options ?? []).map((option) => {
                          const value =
                            typeof option === "string" ? option : option.value;
                          const label =
                            typeof option === "string"
                              ? option
                              : (option.label ?? option.value);
                          return (
                            <label
                              className="dossier-choice-option"
                              key={value}
                            >
                              <input
                                checked={formData[field.key] === value}
                                name={`field-${field.key}`}
                                onChange={() =>
                                  setFormData((current) => ({
                                    ...current,
                                    [field.key]: value,
                                  }))
                                }
                                required={field.required}
                                type="radio"
                                value={value}
                              />
                              <span>{label}</span>
                            </label>
                          );
                        })}
                      </fieldset>
                    ) : field.type === "checkbox" ? (
                      <input
                        checked={formData[field.key] === true}
                        className="ml-3 accent-primary-600"
                        id={`field-${field.key}`}
                        onChange={(event) =>
                          setFormData((current) => ({
                            ...current,
                            [field.key]: event.target.checked,
                          }))
                        }
                        type="checkbox"
                      />
                    ) : (
                      <input
                        className="mt-2 min-h-12 w-full rounded-xl border border-neutral-200 bg-white px-4 text-sm"
                        id={`field-${field.key}`}
                        onChange={(event) =>
                          setFormData((current) => ({
                            ...current,
                            [field.key]:
                              field.type === "number" ||
                              field.type === "currency"
                                ? event.target.value === ""
                                  ? ""
                                  : Number(event.target.value)
                                : event.target.value,
                          }))
                        }
                        placeholder={field.placeholder}
                        required={field.required}
                        type={
                          field.type === "phone"
                            ? "tel"
                            : field.type === "currency"
                              ? "number"
                              : field.type === "address" ||
                                  field.type === "person" ||
                                  field.type === "organization" ||
                                  field.type === "file"
                                ? "text"
                                : field.type
                        }
                        value={
                          typeof formData[field.key] === "string" ||
                          typeof formData[field.key] === "number"
                            ? String(formData[field.key])
                            : ""
                        }
                      />
                    )}
                  </div>
                ))}
              </>
            ) : null}
          </>
        ) : null}
      </section>

      {prepareStep === 3 ? (
        <section
          className="space-y-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-6"
          aria-labelledby="draft-review-title"
        >
          <h2 className="text-xl font-bold" id="draft-review-title">
            Kiểm tra thông tin
          </h2>
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[var(--theme-muted)]">Loại hồ sơ</dt>
              <dd className="mt-1 font-bold">{dossierType?.name}</dd>
            </div>
            <div>
              <dt className="text-[var(--theme-muted)]">Tên hồ sơ</dt>
              <dd className="mt-1 font-bold">{title}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-[var(--theme-muted)]">Mô tả ngắn</dt>
              <dd className="mt-1 whitespace-pre-wrap break-words font-medium">
                {form.getValues("summary")?.trim() || "Chưa điền"}
              </dd>
            </div>
            <div>
              <dt className="text-[var(--theme-muted)]">Thông tin bắt buộc</dt>
              <dd className="mt-1 font-bold">
                {informationComplete}/{informationTotal} đã điền
              </dd>
            </div>
            <div>
              <dt className="text-[var(--theme-muted)]">Chế độ hiển thị</dt>
              <dd className="mt-1 font-bold">
                {form.getValues("visibility") === "PRIVATE"
                  ? "Riêng tư"
                  : form.getValues("visibility") === "UNLISTED"
                    ? "Không niêm yết"
                    : "Công khai"}
              </dd>
            </div>
          </dl>
          {hasTypeSpecificFields ? (
            <div className="border-t border-[var(--theme-border)] pt-4">
              <h3 className="text-sm font-bold">Thông tin theo loại hồ sơ</h3>
              <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                {dossierType?.currentVersion.schema.fields.map((field) => (
                  <div key={field.key}>
                    <dt className="text-[var(--theme-muted)]">
                      {displayFieldLabel(field.label, field.key)}
                    </dt>
                    <dd className="mt-1 whitespace-pre-wrap break-words font-medium">
                      {displayFieldValue(formData[field.key])}
                    </dd>
                  </div>
                ))}
              </dl>
              <p className="mt-3 text-xs leading-5 text-amber-800">
                Sau khi tạo bản nháp, các mục này chưa thể chỉnh sửa. Hãy quay
                lại kiểm tra trước khi lưu.
              </p>
            </div>
          ) : null}
          <div className="rounded-xl border border-primary-200 bg-primary-50 p-4 text-sm text-primary-950">
            <p className="font-bold">Tạo bản nháp trước khi tải tài liệu</p>
            <p className="mt-1 leading-6">
              Bước này chỉ lưu thông tin. Sau đó bạn sẽ tải{" "}
              {documentRules.length} nhóm tài liệu, kiểm tra và nộp hồ sơ. Bản
              nháp chưa được gửi thẩm định.
            </p>
          </div>
        </section>
      ) : null}

      {prepareStep === 3 && create.error ? (
        <div
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800"
          role="alert"
        >
          <p>
            {create.error instanceof ApiError &&
            create.error.code === "APPLICANT_PROFILE_INCOMPLETE"
              ? create.error.message
              : "Không thể tạo hồ sơ. Vui lòng kiểm tra dữ liệu và thử lại."}
          </p>
          {create.error instanceof ApiError &&
          create.error.code === "APPLICANT_PROFILE_INCOMPLETE" ? (
            <a
              className="mt-2 inline-block font-bold underline"
              href="/account"
            >
              Hoàn thiện hồ sơ tài khoản
            </a>
          ) : null}
        </div>
      ) : null}

      {dossierType && prepareStep === 2 ? (
        <section
          aria-label="Tiến độ khai thông tin"
          className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4"
        >
          <div className="flex items-center justify-between gap-4 text-sm">
            <strong>
              {informationComplete}/{informationTotal} thông tin đã hoàn tất
            </strong>
            <span className="text-xs text-neutral-500">
              Bản nháp có thể tiếp tục chỉnh sửa
            </span>
          </div>
          <div
            aria-label={`${informationComplete} trên ${informationTotal} thông tin hoàn tất`}
            aria-valuemax={informationTotal}
            aria-valuemin={0}
            aria-valuenow={informationComplete}
            className="mt-3 h-2 overflow-hidden rounded-full bg-[var(--theme-elevated)]"
            role="progressbar"
          >
            <div
              className="h-full rounded-full bg-primary-600 transition-[width]"
              style={{
                width: `${(informationComplete / informationTotal) * 100}%`,
              }}
            />
          </div>
        </section>
      ) : null}

      {stepError && (prepareStep === 1 || prepareStep === 2) ? (
        <p
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800"
          role="alert"
        >
          {stepError}
        </p>
      ) : null}
      {hasDossierTypes ? (
        <div className="flex flex-wrap justify-end gap-3">
          {prepareStep > 0 ? (
            <Button
              onClick={() => {
                setStepError("");
                setPrepareStep(
                  prepareStep === 3
                    ? hasTypeSpecificFields
                      ? 2
                      : 1
                    : prepareStep === 2
                      ? 1
                      : 0,
                );
              }}
              type="button"
              variant="outline"
            >
              Quay lại
            </Button>
          ) : null}
          {prepareStep === 0 ? (
            <Button
              disabled={!dossierType}
              onClick={() => setPrepareStep(1)}
              type="button"
            >
              Tiếp tục nhập thông tin{" "}
              <ArrowRight aria-hidden="true" className="size-4" />
            </Button>
          ) : prepareStep === 1 ? (
            <Button onClick={() => void reviewCoreInformation()} type="button">
              {hasTypeSpecificFields
                ? "Tiếp tục thông tin theo loại"
                : "Kiểm tra thông tin"}{" "}
              <ArrowRight aria-hidden="true" className="size-4" />
            </Button>
          ) : prepareStep === 2 ? (
            <Button onClick={reviewAdditionalInformation} type="button">
              Kiểm tra thông tin{" "}
              <ArrowRight aria-hidden="true" className="size-4" />
            </Button>
          ) : (
            <Button
              className="min-w-44"
              disabled={
                create.isPending ||
                recovery.dirty ||
                recovery.saving ||
                Boolean(recovery.conflict)
              }
              type="submit"
            >
              <FilePlus2 aria-hidden="true" className="size-4" />
              {create.isPending ? "Đang tạo…" : "Tạo hồ sơ nháp"}
              <ArrowRight aria-hidden="true" className="size-4" />
            </Button>
          )}
        </div>
      ) : null}
    </form>
  );
}
