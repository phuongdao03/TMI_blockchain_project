"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  FileCheck2,
  FilePlus2,
  Files,
  ListChecks,
  ShieldCheck,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm, useWatch } from "react-hook-form";
import { useState } from "react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { ApiError, dossierApi } from "@/lib/api/client";
import { dossierKeys } from "@/lib/dossiers/query-keys";

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

function formatFileLimit(bytes: number): string {
  const megabytes = bytes / 1024 / 1024;
  return `${new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 }).format(megabytes)} MB`;
}

export function DossierCreateForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [dossierTypeVersionId, setDossierTypeVersionId] = useState("");
  const [formData, setFormData] = useState<Record<string, unknown>>({});
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
  const title = useWatch({ control: form.control, name: "title" });
  const dossierType = dossierTypes.data?.find(
    (item) => item.currentVersion.id === dossierTypeVersionId,
  );
  const dossierTypeDescription = dossierType?.currentVersion.schema.description;
  const documentRules = dossierType?.currentVersion.schema.documentRules ?? [];
  const requiredFieldCount =
    dossierType?.currentVersion.schema.fields.filter((field) => field.required)
      .length ?? 0;
  const requiredFields =
    dossierType?.currentVersion.schema.fields.filter(
      (field) => field.required,
    ) ?? [];
  const informationTotal = 1 + requiredFields.length;
  const informationComplete =
    (title.trim().length >= 3 ? 1 : 0) +
    requiredFields.filter((field) => hasRequiredValue(formData[field.key]))
      .length;
  const create = useMutation({
    mutationFn: dossierApi.create,
    onSuccess: async (dossier) => {
      await queryClient.invalidateQueries({ queryKey: dossierKeys.lists() });
      router.push(`/dossiers/${dossier.id}`);
    },
  });

  const submit = form.handleSubmit((values) => {
    if (!dossierType) return;
    create.mutate({
      categoryId: dossierType.categoryId,
      title: values.title,
      summary: values.summary || null,
      visibility: values.visibility,
      dossierTypeVersionId,
      formData,
    });
  });

  return (
    <form className="dossier-create-form space-y-6" onSubmit={submit}>
      <nav aria-label="Các bước gửi hồ sơ">
        <ol className="dossier-journey grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["01", "Chọn loại hồ sơ", "Đang thực hiện"],
            ["02", "Khai thông tin", "Theo biểu mẫu"],
            ["03", "Tải tài liệu", "Sau khi tạo bản nháp"],
            ["04", "Kiểm tra & nộp", "Khóa phiên bản"],
          ].map(([number, label, note], index) => (
            <li
              className={`rounded-xl border p-3 ${
                index === 0
                  ? "border-primary-300 bg-primary-50/60"
                  : "border-[var(--theme-border)] bg-[var(--theme-surface)]"
              }`}
              key={number}
            >
              <span className="font-mono text-xs font-bold text-primary-700">
                {number}
              </span>
              <strong className="ml-2 text-sm">{label}</strong>
              <span className="mt-1 block pl-7 text-xs text-neutral-500">
                {note}
              </span>
            </li>
          ))}
        </ol>
      </nav>
      <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div className="border-b border-neutral-100 bg-neutral-50/70 px-5 py-4 sm:px-6">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            Danh mục hồ sơ
          </p>
        </div>
        <div className="flex items-start gap-4 p-5 sm:p-6">
          <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary-700">
            <ShieldCheck aria-hidden="true" className="size-5" />
          </span>
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
      </section>

      <section className="space-y-5 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
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
          <div className="mt-3 grid max-h-[23rem] gap-3 overflow-y-auto pr-1 sm:grid-cols-2">
            {dossierTypes.data?.map((item) => {
              const selected = item.currentVersion.id === dossierTypeVersionId;
              const description = item.currentVersion.schema.description;
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
                  </span>
                </label>
              );
            })}
          </div>
          {dossierTypes.isError ? (
            <p className="mt-2 text-sm text-error" role="alert">
              Không thể tải loại hồ sơ.
            </p>
          ) : null}
          {dossierTypes.isLoading ? (
            <p className="mt-3 text-sm text-neutral-500">
              Đang tải danh mục hồ sơ…
            </p>
          ) : null}
        </fieldset>

        {dossierType ? (
          <section
            aria-labelledby="document-preflight-title"
            className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 sm:p-5"
          >
            <div className="flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary-700">
                <ListChecks aria-hidden="true" className="size-5" />
              </span>
              <div>
                <h2 className="font-bold" id="document-preflight-title">
                  Tài liệu cần chuẩn bị
                </h2>
                <p className="mt-1 text-sm leading-6 text-neutral-600">
                  {requiredFieldCount} trường thông tin bắt buộc ·{" "}
                  {documentRules.length} nhóm tài liệu. Tệp được tải lên sau khi
                  bản nháp được tạo.
                </p>
              </div>
            </div>

            {documentRules.length ? (
              <ul className="mt-4 grid gap-3 lg:grid-cols-2" role="list">
                {documentRules.map((rule) => (
                  <li
                    className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4"
                    key={rule.key}
                  >
                    <div className="flex items-start gap-3">
                      <FileCheck2
                        aria-hidden="true"
                        className="mt-0.5 size-5 shrink-0 text-primary-700"
                      />
                      <div className="min-w-0">
                        <p className="text-sm font-bold">
                          {rule.label ?? rule.documentType}
                          {rule.required ? (
                            <span className="ml-2 text-xs text-primary-700">
                              Bắt buộc
                            </span>
                          ) : null}
                        </p>
                        <p className="mt-1 text-xs leading-5 text-neutral-600">
                          {rule.allowedMimeTypes
                            .map((mime) => mimeLabels[mime] ?? mime)
                            .join(", ")}{" "}
                          · tối đa {formatFileLimit(rule.maxBytes)} ·{" "}
                          {rule.maxCount ?? 1} tệp
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="mt-4 flex items-start gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 text-sm text-neutral-600">
                <Files aria-hidden="true" className="size-5 shrink-0" />
                Loại hồ sơ này chưa yêu cầu nhóm tệp riêng. Bạn vẫn có thể bổ
                sung bằng chứng trong bản nháp.
              </div>
            )}
          </section>
        ) : null}
        <div>
          <label
            className="text-sm font-bold text-neutral-900"
            htmlFor="dossier-title"
          >
            Tên tài sản hoặc tác phẩm
          </label>
          <input
            aria-describedby="dossier-title-error"
            className="mt-2 min-h-12 w-full rounded-xl border border-neutral-200 bg-white px-4 text-sm outline-none transition focus:border-primary-500 focus:ring-4 focus:ring-primary-100"
            id="dossier-title"
            placeholder="Ví dụ: Bộ nhận diện thương hiệu TMI"
            {...form.register("title")}
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
              ["PRIVATE", "Riêng tư", "Chỉ chủ hồ sơ và người xử lý"],
              ["UNLISTED", "Không niêm yết", "Chỉ người có liên kết"],
              ["PUBLIC", "Công khai", "Có thể công bố sau cấp chứng thư"],
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

        {dossierType?.currentVersion.schema.fields.map((field) => (
          <div key={field.key}>
            <label
              className="text-sm font-bold text-neutral-900"
              htmlFor={`field-${field.key}`}
            >
              {field.label || field.key}
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
                <legend className="sr-only">{field.label || field.key}</legend>
                {(field.options ?? []).map((option) => {
                  const value =
                    typeof option === "string" ? option : option.value;
                  const label =
                    typeof option === "string"
                      ? option
                      : (option.label ?? option.value);
                  return (
                    <label className="dossier-choice-option" key={value}>
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
                      field.type === "number" || field.type === "currency"
                        ? Number(event.target.value)
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
      </section>

      {create.error ? (
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

      {dossierType ? (
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

      <div className="flex flex-col-reverse justify-end gap-3 sm:flex-row">
        <Button
          className="min-w-44"
          disabled={create.isPending || !dossierType}
          type="submit"
        >
          <FilePlus2 aria-hidden="true" className="size-4" />
          {create.isPending ? "Đang tạo…" : "Tạo hồ sơ nháp"}
          <ArrowRight aria-hidden="true" className="size-4" />
        </Button>
      </div>
    </form>
  );
}
