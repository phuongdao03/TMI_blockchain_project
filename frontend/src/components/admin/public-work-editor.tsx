"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  ArrowDown,
  ArrowUp,
  Check,
  CircleAlert,
  Eye,
  FilePenLine,
  ImageIcon,
  Monitor,
  Plus,
  Search,
  Send,
  ShieldAlert,
  Smartphone,
  Trash2,
} from "lucide-react";
import Image from "next/image";
import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { SelectControl } from "@/components/ui/form-controls";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { ApiError, publicWorkAdminApi } from "@/lib/api/client";
import type {
  PublicationStatus,
  PublicWorkEditor as PublicWorkEditorData,
  PublicWorkMedia,
  PublicVideoPresentationInput,
  PublicMediaCandidate,
} from "@/lib/api/types";

const editorSchema = z.object({
  slug: z
    .string()
    .min(1, "Đường dẫn công khai là bắt buộc.")
    .max(180)
    .regex(
      /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
      "Chỉ dùng chữ thường, số và dấu gạch nối.",
    ),
  title: z.string().trim().min(3, "Tiêu đề cần ít nhất 3 ký tự.").max(255),
  shortDescription: z
    .string()
    .trim()
    .min(10, "Mô tả ngắn cần ít nhất 10 ký tự.")
    .max(500),
  fullDescription: z.string().max(20_000).nullable(),
  authorDisplayName: z.string().max(255).nullable(),
  categoryId: z.string().uuid("Hãy chọn danh mục."),
  visibility: z.enum(["PRIVATE", "UNLISTED", "PUBLIC"]),
  thumbnailMediaId: z.string().uuid().nullable(),
  tagIds: z.array(z.string().uuid()).max(50),
});

type EditorValues = z.infer<typeof editorSchema>;
type StateAction = "publish" | "hide" | "suspend" | "archive";

const fieldClass =
  "min-h-11 w-full rounded-xl border border-neutral-200 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-100";

const statusLabels: Record<PublicationStatus, string> = {
  DRAFT: "Bản nháp",
  PENDING_PUBLICATION: "Chờ xuất bản",
  PUBLISHED: "Đã xuất bản",
  HIDDEN: "Đang ẩn",
  SUSPENDED: "Tạm ngưng",
  ARCHIVED: "Đã lưu trữ",
};

const checklistLabels: Record<string, string> = {
  TITLE_REQUIRED: "Có tiêu đề công khai",
  SHORT_DESCRIPTION_REQUIRED: "Có mô tả ngắn",
  ACTIVE_CATEGORY_REQUIRED: "Danh mục đang hoạt động",
  APPROVED_DOSSIER_REQUIRED: "Hồ sơ đã được phê duyệt",
  ACTIVE_CERTIFICATE_REQUIRED: "Chứng nhận còn hiệu lực",
  READY_THUMBNAIL_REQUIRED: "Ảnh bìa hoặc video công khai đã sẵn sàng",
};

const derivativeStatusLabels: Record<
  PublicWorkMedia["derivativeStatus"],
  string
> = {
  PENDING: "Đang chờ xử lý",
  PROCESSING: "Đang tối ưu bản trình chiếu",
  READY: "Sẵn sàng công bố",
  FAILED: "Xử lý chưa thành công",
};

function tagSlug(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function defaults(work: PublicWorkEditorData): EditorValues {
  return {
    slug: work.slug,
    title: work.title,
    shortDescription: work.shortDescription,
    fullDescription: work.fullDescription,
    authorDisplayName: work.authorDisplayName,
    categoryId: work.categoryId,
    visibility: work.visibility,
    thumbnailMediaId: work.thumbnailMediaId,
    tagIds: work.tagIds,
  };
}

type PublicWorkEditorProps = {
  initialSelectedId?: string;
};

export function PublicWorkEditor({
  initialSelectedId,
}: PublicWorkEditorProps = {}) {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<PublicationStatus | "">("DRAFT");
  const [selectedId, setSelectedId] = useState<string | undefined>(
    initialSelectedId,
  );
  const [previewMode, setPreviewMode] = useState<"desktop" | "mobile">(
    "desktop",
  );
  const [showPreview, setShowPreview] = useState(false);
  const [pendingAction, setPendingAction] = useState<StateAction>();
  const [reason, setReason] = useState("");
  const [newTagName, setNewTagName] = useState("");

  const works = useQuery({
    queryKey: ["admin", "public-works", query, status],
    queryFn: () =>
      publicWorkAdminApi.list({
        query: query || undefined,
        status: status || undefined,
        pageSize: 50,
      }),
  });
  const detail = useQuery({
    queryKey: ["admin", "public-work", selectedId],
    queryFn: () => publicWorkAdminApi.get(selectedId!),
    enabled: Boolean(selectedId),
  });
  const categories = useQuery({
    queryKey: ["admin", "public-work-categories"],
    queryFn: publicWorkAdminApi.categories,
  });
  const tags = useQuery({
    queryKey: ["admin", "public-work-tags"],
    queryFn: publicWorkAdminApi.tags,
  });
  const media = useQuery({
    queryKey: ["admin", "public-work-media", selectedId],
    queryFn: () => publicWorkAdminApi.media(selectedId!),
    enabled: Boolean(selectedId),
    refetchInterval: (query) =>
      query.state.data?.some((item) =>
        ["PENDING", "PROCESSING"].includes(item.derivativeStatus),
      )
        ? 4_000
        : false,
    refetchIntervalInBackground: false,
  });
  const mediaCandidates = useQuery({
    queryKey: ["admin", "public-work-media-candidates", selectedId],
    queryFn: () => publicWorkAdminApi.mediaCandidates(selectedId!),
    enabled: Boolean(selectedId),
  });
  const preview = useQuery({
    queryKey: ["admin", "public-work-preview", selectedId],
    queryFn: () => publicWorkAdminApi.preview(selectedId!),
    enabled: Boolean(selectedId && showPreview),
  });

  const {
    control,
    formState: { errors, isDirty },
    handleSubmit,
    getValues,
    register,
    reset,
    setValue,
  } = useForm<EditorValues>({
    resolver: zodResolver(editorSchema),
    defaultValues: {
      slug: "",
      title: "",
      shortDescription: "",
      fullDescription: null,
      authorDisplayName: null,
      categoryId: "",
      visibility: "PUBLIC",
      thumbnailMediaId: null,
      tagIds: [],
    },
  });

  useEffect(() => {
    if (detail.data) reset(defaults(detail.data));
  }, [detail.data, reset]);

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (!isDirty) return;
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isDirty]);

  const refreshWork = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["admin", "public-work", selectedId],
      }),
      queryClient.invalidateQueries({ queryKey: ["admin", "public-works"] }),
      queryClient.invalidateQueries({
        queryKey: ["admin", "public-work-preview", selectedId],
      }),
    ]);
  };

  const save = useMutation({
    mutationFn: async (values: EditorValues) => {
      if (!selectedId || !detail.data) throw new Error("Chưa chọn tác phẩm.");
      const updated = await publicWorkAdminApi.update(selectedId, {
        expectedVersion: detail.data.version,
        slug: values.slug,
        title: values.title,
        shortDescription: values.shortDescription,
        fullDescription: values.fullDescription || null,
        authorDisplayName: values.authorDisplayName || null,
        categoryId: values.categoryId,
        tagIds: values.tagIds,
        visibility: values.visibility,
        thumbnailMediaId: values.thumbnailMediaId,
      });
      return updated;
    },
    onSuccess: async (updated) => {
      reset(defaults(updated));
      await refreshWork();
    },
  });

  const transition = useMutation({
    mutationFn: async (action: StateAction) => {
      if (!selectedId || !detail.data) throw new Error("Chưa chọn tác phẩm.");
      if (action === "publish") {
        return publicWorkAdminApi.publish(selectedId, detail.data.version);
      }
      return publicWorkAdminApi.transition(
        selectedId,
        action,
        detail.data.version,
        reason || undefined,
      );
    },
    onSuccess: async () => {
      setPendingAction(undefined);
      setReason("");
      await refreshWork();
    },
  });

  const selectedTags = useWatch({ control, name: "tagIds" }) ?? [];
  const createTag = useMutation({
    mutationFn: (name: string) =>
      publicWorkAdminApi.createTag({
        name: name.trim(),
        slug: tagSlug(name),
        isActive: true,
      }),
    onSuccess: async (created) => {
      setValue("tagIds", [...selectedTags, created.id], { shouldDirty: true });
      setNewTagName("");
      await queryClient.invalidateQueries({
        queryKey: ["admin", "public-work-tags"],
      });
    },
  });
  const selectedThumbnail = useWatch({
    control,
    name: "thumbnailMediaId",
  });
  const checklistPassed =
    detail.data?.checklist.filter((item) => item.passed).length ?? 0;
  const saveError = save.error as ApiError | null;

  return (
    <section className="cms-workspace overflow-visible rounded-3xl border border-neutral-200 bg-white shadow-sm">
      <div className="grid min-h-[46rem] lg:grid-cols-[20rem_minmax(0,1fr)]">
        <aside className="cms-list-pane border-b border-neutral-200 bg-neutral-50/80 lg:border-r lg:border-b-0">
          <div className="border-b border-neutral-200 p-4">
            <div className="relative">
              <Search
                aria-hidden="true"
                className="absolute top-3 left-3 size-4 text-neutral-500"
              />
              <input
                aria-label="Tìm tác phẩm"
                className={`${fieldClass} pl-9`}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Tìm theo tiêu đề hoặc đường dẫn"
                value={query}
              />
            </div>
            <SelectControl
              aria-label="Lọc theo trạng thái"
              className={`${fieldClass} mt-3`}
              onChange={(event) =>
                setStatus(event.target.value as PublicationStatus | "")
              }
              value={status}
            >
              <option value="">Tất cả trạng thái</option>
              {Object.entries(statusLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </SelectControl>
          </div>
          <div className="max-h-80 overflow-y-auto p-2 lg:max-h-[38rem]">
            {works.isPending ? (
              <div className="space-y-2 p-2" role="status">
                <span className="sr-only">Đang tải danh sách…</span>
                {[0, 1, 2, 3].map((item) => (
                  <div
                    aria-hidden="true"
                    className="dashboard-skeleton h-16 animate-pulse rounded-xl"
                    key={item}
                  />
                ))}
              </div>
            ) : null}
            {works.isError ? (
              <div className="p-4 text-sm" role="alert">
                <p className="font-bold">Chưa thể tải nội dung</p>
                <p className="mt-1 text-neutral-500">
                  Vui lòng kiểm tra kết nối và thử lại.
                </p>
                <button
                  className="mt-3 min-h-11 font-bold text-primary-700"
                  onClick={() => void works.refetch()}
                  type="button"
                >
                  Thử lại
                </button>
              </div>
            ) : null}
            {works.data?.data.map((work) => (
              <button
                className={`cms-list-item mb-1 w-full rounded-xl border px-3 py-3 text-left transition ${selectedId === work.id ? "cms-list-item--selected border-primary-200 bg-white shadow-sm" : "border-transparent"}`}
                key={work.id}
                onClick={() => {
                  if (isDirty && !window.confirm("Bỏ các thay đổi chưa lưu?"))
                    return;
                  setSelectedId(work.id);
                  setShowPreview(false);
                }}
                type="button"
              >
                <span className="block truncate font-mono text-sm font-black text-primary-800">
                  {work.dossierCode ||
                    `TP-${work.id.slice(0, 8).toUpperCase()}`}
                </span>
                <span className="mt-1 block line-clamp-2 text-xs font-semibold text-neutral-700">
                  {work.title}
                </span>
                <span className="mt-2 flex items-center justify-between gap-2 text-xs text-neutral-500">
                  <span className="truncate">Mã tác phẩm</span>
                  <span>{statusLabels[work.publicationStatus]}</span>
                </span>
              </button>
            ))}
            {!works.isPending && works.data?.data.length === 0 ? (
              <p className="p-4 text-sm leading-6 text-neutral-500">
                Không có tác phẩm phù hợp bộ lọc.
              </p>
            ) : null}
          </div>
        </aside>

        {!selectedId ? (
          <div className="grid place-items-center p-8 text-center">
            <div className="max-w-sm">
              <FilePenLine className="mx-auto size-10 text-primary-600" />
              <h2 className="mt-4 text-xl font-bold">
                Chọn một tác phẩm để biên tập
              </h2>
              <p className="mt-2 text-sm leading-6 text-neutral-500">
                Thông tin, hình ảnh và bản xem trước sẽ sử dụng dữ liệu mới nhất
                đã lưu trên hệ thống.
              </p>
            </div>
          </div>
        ) : detail.isPending ? (
          <div className="p-8 text-sm text-neutral-500">
            Đang mở trình biên tập…
          </div>
        ) : detail.data ? (
          <div className="min-w-0">
            <div className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 border-b border-neutral-200 bg-white/95 px-5 py-4 backdrop-blur">
              <div>
                <p className="text-xs font-bold tracking-[0.16em] text-primary-700 uppercase">
                  Public catalog
                </p>
                <h2 className="mt-1 text-xl font-bold tracking-tight">
                  {detail.data.title}
                </h2>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => setShowPreview((value) => !value)}
                  variant="outline"
                >
                  <Eye className="size-4" />{" "}
                  {showPreview ? "Đóng xem trước" : "Xem trước"}
                </Button>
                <Button
                  disabled={!isDirty || save.isPending}
                  onClick={handleSubmit((values) => save.mutate(values))}
                >
                  <Check className="size-4" />{" "}
                  {save.isPending ? "Đang lưu…" : "Lưu thay đổi"}
                </Button>
              </div>
            </div>

            {showPreview ? (
              <PreviewPanel
                data={preview.data}
                loading={preview.isPending}
                mode={previewMode}
                onMode={setPreviewMode}
              />
            ) : (
              <form
                className="grid gap-6 p-5 xl:grid-cols-[minmax(0,1fr)_19rem]"
                onSubmit={handleSubmit((values) => save.mutate(values))}
              >
                <div className="space-y-5">
                  <SourceFieldsPanel
                    fields={detail.data.sourceFields}
                    onDescription={(value) =>
                      setValue("shortDescription", value, { shouldDirty: true })
                    }
                    onFullDescription={(value) => {
                      const current = getValues("fullDescription");
                      setValue(
                        "fullDescription",
                        current ? `${current}\n\n${value}` : value,
                        { shouldDirty: true },
                      );
                    }}
                    onTitle={(value) =>
                      setValue("title", value, { shouldDirty: true })
                    }
                    version={detail.data.sourceVersionNo}
                  />
                  <Gallery
                    candidates={mediaCandidates.data ?? []}
                    items={media.data ?? []}
                    onChanged={() => {
                      void queryClient.invalidateQueries({
                        queryKey: ["admin", "public-work-media", selectedId],
                      });
                      void queryClient.invalidateQueries({
                        queryKey: [
                          "admin",
                          "public-work-media-candidates",
                          selectedId,
                        ],
                      });
                    }}
                    onRetry={() => {
                      void mediaCandidates.refetch();
                      void media.refetch();
                    }}
                    onThumbnail={(assetId) =>
                      setValue("thumbnailMediaId", assetId, {
                        shouldDirty: true,
                      })
                    }
                    selectedThumbnail={selectedThumbnail}
                    sourceError={mediaCandidates.error ?? media.error}
                    sourceLoading={mediaCandidates.isPending || media.isPending}
                    workId={selectedId}
                  />
                  <EditorField
                    error={errors.title?.message}
                    label="Tiêu đề công khai"
                  >
                    <input className={fieldClass} {...register("title")} />
                  </EditorField>
                  <input type="hidden" {...register("slug")} />
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <p className="mb-2 text-sm font-bold text-neutral-800">
                        Đường dẫn công khai
                      </p>
                      <output className="flex min-h-11 items-center overflow-hidden rounded-xl border border-neutral-200 bg-neutral-50 px-3 font-mono text-sm text-neutral-700">
                        <span className="truncate">
                          /works/{detail.data.id}
                        </span>
                      </output>
                    </div>
                    <EditorField
                      error={errors.authorDisplayName?.message}
                      label="Tên tác giả hiển thị"
                    >
                      <input
                        className={fieldClass}
                        {...register("authorDisplayName")}
                      />
                    </EditorField>
                  </div>
                  <EditorField
                    error={errors.shortDescription?.message}
                    label="Mô tả ngắn"
                  >
                    <textarea
                      className={`${fieldClass} min-h-28 py-3`}
                      {...register("shortDescription")}
                    />
                  </EditorField>
                  <EditorField
                    error={errors.fullDescription?.message}
                    label="Nội dung giới thiệu"
                  >
                    <textarea
                      className={`${fieldClass} min-h-52 py-3`}
                      {...register("fullDescription")}
                    />
                  </EditorField>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <EditorField
                      error={errors.categoryId?.message}
                      label="Danh mục"
                    >
                      <SelectControl
                        className={fieldClass}
                        {...register("categoryId")}
                      >
                        <option value="">Chọn danh mục</option>
                        {categories.data
                          ?.filter((item) => item.isActive)
                          .map((item) => (
                            <option key={item.id} value={item.id}>
                              {item.name}
                            </option>
                          ))}
                      </SelectControl>
                    </EditorField>
                    <EditorField label="Phạm vi hiển thị">
                      <SelectControl
                        className={fieldClass}
                        {...register("visibility")}
                      >
                        <option value="PUBLIC">Công khai</option>
                        <option value="UNLISTED">Chỉ người có liên kết</option>
                        <option value="PRIVATE">Riêng tư</option>
                      </SelectControl>
                    </EditorField>
                  </div>
                  <fieldset className="min-w-0 rounded-2xl border border-neutral-200 p-4">
                    <legend className="text-sm font-bold text-neutral-800">
                      Thẻ phân loại
                    </legend>
                    <div className="mt-2 flex min-h-10 flex-wrap gap-2">
                      {tags.data
                        ?.filter((tag) => tag.isActive)
                        .map((tag) => {
                          const active = selectedTags.includes(tag.id);
                          return (
                            <button
                              aria-pressed={active}
                              className={`min-h-10 rounded-full border px-3 text-sm font-semibold transition ${active ? "border-primary-600 bg-primary-50 text-primary-700" : "border-neutral-200 text-neutral-600 hover:border-neutral-400"}`}
                              key={tag.id}
                              onClick={() =>
                                setValue(
                                  "tagIds",
                                  active
                                    ? selectedTags.filter((id) => id !== tag.id)
                                    : [...selectedTags, tag.id],
                                  { shouldDirty: true },
                                )
                              }
                              type="button"
                            >
                              {tag.name}
                            </button>
                          );
                        })}
                      {tags.data?.filter((tag) => tag.isActive).length === 0 ? (
                        <p className="self-center text-sm text-neutral-500">
                          Chưa có thẻ phân loại khả dụng.
                        </p>
                      ) : null}
                    </div>
                    <div className="mt-4 flex flex-col gap-2 border-t border-neutral-100 pt-4 sm:flex-row">
                      <label className="sr-only" htmlFor="new-public-work-tag">
                        Tên thẻ mới
                      </label>
                      <input
                        className={`${fieldClass} min-w-0 flex-1`}
                        id="new-public-work-tag"
                        onChange={(event) => setNewTagName(event.target.value)}
                        placeholder="Ví dụ: Video thương hiệu"
                        value={newTagName}
                      />
                      <Button
                        disabled={
                          createTag.isPending ||
                          tagSlug(newTagName).length === 0
                        }
                        onClick={() => createTag.mutate(newTagName)}
                        type="button"
                        variant="outline"
                      >
                        <Plus className="size-4" />
                        {createTag.isPending ? "Đang tạo…" : "Tạo thẻ"}
                      </Button>
                    </div>
                    {createTag.isError ? (
                      <p className="mt-2 text-sm text-red-700" role="alert">
                        Không thể tạo thẻ. Hãy kiểm tra tên thẻ hoặc thử lại.
                      </p>
                    ) : null}
                  </fieldset>
                  {saveError ? (
                    <p
                      aria-live="polite"
                      className="rounded-xl bg-red-50 p-3 text-sm text-red-800"
                    >
                      {saveError.code === "PUBLIC_WORK_VERSION_CONFLICT"
                        ? "Tác phẩm đã được người khác cập nhật. Tải lại dữ liệu trước khi sửa tiếp."
                        : saveError.message}
                    </p>
                  ) : null}
                </div>

                <aside className="space-y-4">
                  <section className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="font-bold">Điều kiện xuất bản</h3>
                      <span className="text-xs font-bold text-neutral-500">
                        {checklistPassed}/{detail.data.checklist.length}
                      </span>
                    </div>
                    <ul className="mt-3 space-y-2">
                      {detail.data.checklist.map((item) => (
                        <li className="flex gap-2 text-sm" key={item.code}>
                          {item.passed ? (
                            <Check className="mt-0.5 size-4 shrink-0 text-green-700" />
                          ) : (
                            <CircleAlert className="mt-0.5 size-4 shrink-0 text-amber-700" />
                          )}
                          <span
                            className={
                              item.passed
                                ? "text-neutral-700"
                                : "text-neutral-950"
                            }
                          >
                            {checklistLabels[item.code] ?? item.code}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </section>
                  <section className="rounded-2xl border border-neutral-200 p-4">
                    <p className="text-xs font-bold tracking-wide text-neutral-500 uppercase">
                      Trạng thái
                    </p>
                    <p className="mt-1 font-bold">
                      {statusLabels[detail.data.publicationStatus]}
                    </p>
                    <p className="mt-1 text-xs text-neutral-500">
                      Phiên bản {detail.data.version}
                    </p>
                    <div className="mt-4 grid gap-2">
                      {detail.data.publicationStatus !== "PUBLISHED" ? (
                        <Button
                          disabled={
                            !detail.data.checklist.every(
                              (item) => item.passed,
                            ) || isDirty
                          }
                          onClick={() => setPendingAction("publish")}
                        >
                          <Send className="size-4" /> Xuất bản
                        </Button>
                      ) : (
                        <Button
                          onClick={() => setPendingAction("hide")}
                          variant="outline"
                        >
                          <Eye className="size-4" /> Ẩn tác phẩm
                        </Button>
                      )}
                      <Button
                        onClick={() => setPendingAction("suspend")}
                        variant="outline"
                      >
                        <ShieldAlert className="size-4" /> Tạm ngưng
                      </Button>
                      <Button
                        onClick={() => setPendingAction("archive")}
                        variant="ghost"
                      >
                        <Archive className="size-4" /> Lưu trữ
                      </Button>
                    </div>
                    {isDirty ? (
                      <p className="mt-3 text-xs leading-5 text-amber-700">
                        Hãy lưu thay đổi trước khi chuyển trạng thái.
                      </p>
                    ) : null}
                  </section>
                </aside>
              </form>
            )}
          </div>
        ) : (
          <div className="p-8 text-sm text-red-700">
            Không thể tải dữ liệu tác phẩm.
          </div>
        )}
      </div>

      <ConfirmationDialog
        confirmLabel={pendingAction === "publish" ? "Xuất bản" : "Ẩn tác phẩm"}
        description={
          pendingAction === "publish"
            ? "Tác phẩm sẽ xuất hiện trong danh mục công khai ngay lập tức."
            : "Tác phẩm sẽ không còn xuất hiện trong danh mục công khai."
        }
        isPending={transition.isPending}
        onCancel={() => setPendingAction(undefined)}
        onConfirm={() => pendingAction && transition.mutate(pendingAction)}
        open={pendingAction === "publish" || pendingAction === "hide"}
        title={
          pendingAction === "publish"
            ? "Xác nhận xuất bản"
            : "Xác nhận ẩn tác phẩm"
        }
      />
      <ReasonDialog
        action={pendingAction}
        isPending={transition.isPending}
        onCancel={() => {
          setPendingAction(undefined);
          setReason("");
        }}
        onConfirm={() => pendingAction && transition.mutate(pendingAction)}
        onReason={setReason}
        reason={reason}
      />
    </section>
  );
}

function SourceFieldsPanel({
  fields,
  onDescription,
  onFullDescription,
  onTitle,
  version,
}: {
  fields: PublicWorkEditorData["sourceFields"];
  onDescription: (value: string) => void;
  onFullDescription: (value: string) => void;
  onTitle: (value: string) => void;
  version: number;
}) {
  return (
    <section className="rounded-2xl border border-primary-200 bg-primary-50/50 p-4">
      <p className="text-sm font-bold text-primary-950">
        Dữ liệu hồ sơ gốc · Phiên bản {version}
      </p>
      <p className="mt-1 text-xs leading-5 text-primary-800">
        Chọn thông tin người dùng đã khai trong phiên bản được ký. Dữ liệu gốc
        và dấu vân tay không bị thay đổi.
      </p>
      <ul className="mt-3 grid gap-2">
        {fields.map((field, index) => (
          <li
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary-100 bg-white p-3"
            key={`${field.key}-${index}`}
          >
            <span className="min-w-0 flex-1">
              <span className="block text-xs font-bold text-neutral-500">
                {field.label}
              </span>
              <span className="mt-1 block line-clamp-2 text-sm text-neutral-950">
                {field.value}
              </span>
            </span>
            <Button
              onClick={() => {
                if (field.key === "title") onTitle(field.value);
                else if (field.key === "summary") onDescription(field.value);
                else onFullDescription(`${field.label}: ${field.value}`);
              }}
              type="button"
              variant="outline"
            >
              {field.key === "title"
                ? "Dùng tiêu đề này"
                : field.key === "summary"
                  ? "Dùng mô tả này"
                  : "Thêm vào giới thiệu"}
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function EditorField({
  children,
  error,
  label,
}: {
  children: React.ReactNode;
  error?: string;
  label: string;
}) {
  return (
    <label className="block text-sm font-bold text-neutral-800">
      {label}
      <span className="mt-2 block">{children}</span>
      {error ? (
        <span className="mt-1 block text-xs font-medium text-red-700">
          {error}
        </span>
      ) : null}
    </label>
  );
}

function Gallery({
  candidates,
  items,
  onChanged,
  onRetry,
  onThumbnail,
  selectedThumbnail,
  sourceError,
  sourceLoading,
  workId,
}: {
  candidates: PublicMediaCandidate[];
  items: PublicWorkMedia[];
  onChanged: () => void;
  onRetry: () => void;
  onThumbnail: (assetId: string) => void;
  selectedThumbnail: string | null;
  sourceError: unknown;
  sourceLoading: boolean;
  workId: string;
}) {
  const [attachingId, setAttachingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const availableCandidates = candidates.filter(
    (candidate) => !candidate.alreadyAttached,
  );

  const reorder = async (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= items.length) return;
    const ids = items.map((item) => item.id);
    [ids[index], ids[target]] = [ids[target]!, ids[index]!];
    await publicWorkAdminApi.reorderMedia(workId, ids);
    onChanged();
  };
  const remove = async (relationId: string) => {
    await publicWorkAdminApi.removeMedia(workId, relationId);
    onChanged();
  };
  const attachCandidate = async (candidate: PublicMediaCandidate) => {
    if (
      candidate.accessScope !== "PUBLIC" &&
      candidate.accessScope !== "PUBLIC_PREVIEW" &&
      !window.confirm(
        "Tài liệu này đang được phân loại riêng tư. Chỉ tiếp tục nếu đây chính là tác phẩm cần công bố, không phải giấy tờ định danh hoặc bằng chứng quyền sở hữu.",
      )
    ) {
      return;
    }
    setActionError(null);
    setAttachingId(candidate.mediaAssetId);
    try {
      await publicWorkAdminApi.attachMedia(
        workId,
        candidate.mediaAssetId,
        items.length,
        {
          caption: candidate.title,
          altText: candidate.kind === "IMAGE" ? candidate.title : undefined,
        },
      );
      onChanged();
    } catch (error) {
      setActionError(
        error instanceof Error
          ? error.message
          : "Không thể chọn tài liệu. Vui lòng thử lại.",
      );
    } finally {
      setAttachingId(null);
    }
  };
  return (
    <section
      aria-labelledby="submitted-media-title"
      className="rounded-2xl border border-neutral-200 p-4"
    >
      <div className="flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary-50">
          <ImageIcon className="size-4 text-primary-700" />
        </span>
        <div>
          <h3 className="font-bold" id="submitted-media-title">
            Tài liệu tác phẩm đã nộp
          </h3>
          <p className="mt-1 text-sm leading-6 text-neutral-600">
            Chọn trực tiếp tài liệu thuộc phiên bản hồ sơ đã được xác lập. Không
            cần tải lại tệp; hệ thống giữ nguyên tệp gốc và chỉ tạo bản trình
            chiếu tối ưu.
          </p>
        </div>
      </div>

      {sourceLoading ? (
        <p
          className="mt-4 rounded-xl bg-neutral-50 p-4 text-sm text-neutral-600"
          role="status"
        >
          Đang tải tài liệu của hồ sơ…
        </p>
      ) : sourceError ? (
        <div
          className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4"
          role="alert"
        >
          <p className="text-sm font-semibold text-red-800">
            Không thể tải tài liệu đã nộp. Dữ liệu gốc vẫn được giữ nguyên.
          </p>
          <Button
            className="mt-3"
            onClick={onRetry}
            type="button"
            variant="outline"
          >
            Thử tải lại
          </Button>
        </div>
      ) : availableCandidates.length > 0 ? (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3">
          <p className="text-sm font-bold text-amber-950">
            Chọn tài liệu dùng để công bố
          </p>
          <ul className="mt-3 space-y-2">
            {availableCandidates.map((candidate) => (
              <li
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white p-2"
                key={candidate.mediaAssetId}
              >
                <span className="min-w-0 flex-1 text-sm">
                  <strong className="block truncate">{candidate.title}</strong>
                  <span className="mt-1 block text-xs text-neutral-500">
                    {candidate.filename} · {formatBytes(candidate.bytes)} ·{" "}
                    {candidate.mimeType}
                  </span>
                  <span
                    className={`mt-2 inline-block rounded-full px-2 py-0.5 text-[0.68rem] font-bold ${candidate.accessScope === "PUBLIC" || candidate.accessScope === "PUBLIC_PREVIEW" ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-800"}`}
                  >
                    {candidate.accessScope === "PUBLIC" ||
                    candidate.accessScope === "PUBLIC_PREVIEW"
                      ? "Được phép xem trước"
                      : "Tài liệu riêng tư"}
                  </span>
                </span>
                <Button
                  disabled={attachingId !== null}
                  onClick={() => void attachCandidate(candidate)}
                  type="button"
                  variant="outline"
                >
                  {attachingId === candidate.mediaAssetId
                    ? "Đang chọn…"
                    : "Chọn để công bố"}
                </Button>
              </li>
            ))}
          </ul>
        </div>
      ) : items.length === 0 ? (
        <p className="mt-4 rounded-xl bg-neutral-50 p-4 text-sm leading-6 text-neutral-600">
          Chưa tìm thấy hình ảnh, âm thanh hoặc video trong phiên bản hồ sơ đã
          được xác lập. Hãy kiểm tra lại tài liệu của phiên bản nguồn.
        </p>
      ) : (
        <p className="mt-4 rounded-xl bg-emerald-50 p-3 text-sm font-semibold text-emerald-800">
          Tất cả tài liệu nguồn phù hợp đã được chọn.
        </p>
      )}

      {actionError ? (
        <p
          className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-800"
          role="alert"
        >
          {actionError}
        </p>
      ) : null}

      {items.length > 0 ? (
        <div className="mt-5 border-t border-neutral-200 pt-4">
          <h4 className="text-sm font-bold text-neutral-800">
            Đang dùng để công bố
          </h4>
          <ul className="mt-2 divide-y divide-neutral-200">
            {items.map((item, index) => (
              <li className="py-3" key={item.id}>
                <div className="flex flex-wrap items-center gap-3">
                  <span className="grid size-10 place-items-center rounded-lg bg-neutral-100 text-xs font-bold text-neutral-600">
                    {item.mediaKind.slice(0, 3)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-bold">
                      {item.caption || item.altText || `Media ${index + 1}`}
                    </span>
                    <span className="text-xs font-semibold text-neutral-600">
                      {derivativeStatusLabels[item.derivativeStatus]}
                    </span>
                    {item.derivativeStatus === "PENDING" ||
                    item.derivativeStatus === "PROCESSING" ? (
                      <span className="mt-1 block text-xs text-neutral-500">
                        Tự động cập nhật trạng thái, bạn có thể tiếp tục biên
                        tập.
                      </span>
                    ) : null}
                  </span>
                  {item.mediaKind === "IMAGE" || item.mediaKind === "VIDEO" ? (
                    <button
                      className={`rounded-lg px-2 py-1 text-xs font-bold ${selectedThumbnail === item.mediaAssetId ? "bg-primary-50 text-primary-700" : "text-neutral-600"}`}
                      disabled={item.derivativeStatus !== "READY"}
                      onClick={() => onThumbnail(item.mediaAssetId)}
                      type="button"
                    >
                      {selectedThumbnail === item.mediaAssetId
                        ? "Đang làm bìa"
                        : item.mediaKind === "VIDEO"
                          ? "Dùng khung video làm bìa"
                          : "Đặt ảnh bìa"}
                    </button>
                  ) : null}
                  <button
                    aria-label="Di chuyển lên"
                    disabled={index === 0}
                    onClick={() => void reorder(index, -1)}
                    type="button"
                  >
                    <ArrowUp className="size-4" />
                  </button>
                  <button
                    aria-label="Di chuyển xuống"
                    disabled={index === items.length - 1}
                    onClick={() => void reorder(index, 1)}
                    type="button"
                  >
                    <ArrowDown className="size-4" />
                  </button>
                  <button
                    aria-label="Xóa hình ảnh hoặc video"
                    className="text-red-700"
                    onClick={() => void remove(item.id)}
                    type="button"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>
                {item.mediaKind === "VIDEO" ? (
                  <VideoPresentationSettings
                    images={items.filter(
                      (candidate) => candidate.mediaKind === "IMAGE",
                    )}
                    item={item}
                    onChanged={onChanged}
                    workId={workId}
                  />
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  const megabytes = bytes / (1024 * 1024);
  return `${megabytes >= 10 ? megabytes.toFixed(0) : megabytes.toFixed(1)} MB`;
}

function VideoPresentationSettings({
  images,
  item,
  onChanged,
  workId,
}: {
  images: PublicWorkMedia[];
  item: PublicWorkMedia;
  onChanged: () => void;
  workId: string;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<PublicVideoPresentationInput>({
    posterMediaAssetId: item.posterMediaAssetId,
    controlsPreset: item.videoControlsPreset,
    fitMode: item.videoFitMode,
    qualityProfile: item.videoQualityProfile,
    maxWidth: item.videoMaxWidth as PublicVideoPresentationInput["maxWidth"],
    autoplay: item.videoAutoplay,
    loop: item.videoLoop,
    muted: item.videoMuted,
  });

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await publicWorkAdminApi.configureVideo(workId, item.id, settings);
      onChanged();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể lưu cấu hình video.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <details className="mt-3 rounded-xl border border-neutral-200 bg-neutral-50 p-3">
      <summary className="cursor-pointer text-sm font-bold">
        Cấu hình trình phát video
      </summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="text-xs font-bold">
          Poster
          <select
            className="mt-1 h-10 w-full rounded-lg border border-neutral-300 bg-white px-2 text-sm"
            onChange={(event) =>
              setSettings({
                ...settings,
                posterMediaAssetId: event.target.value || null,
              })
            }
            value={settings.posterMediaAssetId ?? ""}
          >
            <option value="">Khung hình tự động từ video</option>
            {images
              .filter((image) => image.derivativeStatus === "READY")
              .map((image, index) => (
                <option key={image.id} value={image.mediaAssetId}>
                  {image.caption || image.altText || `Ảnh ${index + 1}`}
                </option>
              ))}
          </select>
        </label>
        <label className="text-xs font-bold">
          Điều khiển
          <select
            className="mt-1 h-10 w-full rounded-lg border border-neutral-300 bg-white px-2 text-sm"
            onChange={(event) =>
              setSettings({
                ...settings,
                controlsPreset: event.target
                  .value as PublicVideoPresentationInput["controlsPreset"],
              })
            }
            value={settings.controlsPreset}
          >
            <option value="FULL">Đầy đủ</option>
            <option value="MINIMAL">Tối giản</option>
            <option value="NONE">Ẩn</option>
          </select>
        </label>
        <label className="text-xs font-bold">
          Hiển thị khung
          <select
            className="mt-1 h-10 w-full rounded-lg border border-neutral-300 bg-white px-2 text-sm"
            onChange={(event) =>
              setSettings({
                ...settings,
                fitMode: event.target
                  .value as PublicVideoPresentationInput["fitMode"],
              })
            }
            value={settings.fitMode}
          >
            <option value="CONTAIN">Hiện đầy đủ</option>
            <option value="COVER">Lấp đầy khung</option>
          </select>
        </label>
        <label className="text-xs font-bold">
          Tối ưu chất lượng
          <select
            className="mt-1 h-10 w-full rounded-lg border border-neutral-300 bg-white px-2 text-sm"
            onChange={(event) =>
              setSettings({
                ...settings,
                qualityProfile: event.target
                  .value as PublicVideoPresentationInput["qualityProfile"],
              })
            }
            value={settings.qualityProfile}
          >
            <option value="DATA_SAVER">Tiết kiệm dữ liệu</option>
            <option value="BALANCED">Cân bằng</option>
            <option value="HIGH">Chất lượng cao</option>
          </select>
        </label>
        <label className="text-xs font-bold">
          Độ rộng tối đa
          <select
            className="mt-1 h-10 w-full rounded-lg border border-neutral-300 bg-white px-2 text-sm"
            onChange={(event) =>
              setSettings({
                ...settings,
                maxWidth: Number(
                  event.target.value,
                ) as PublicVideoPresentationInput["maxWidth"],
              })
            }
            value={settings.maxWidth}
          >
            <option value={640}>640px</option>
            <option value={960}>960px</option>
            <option value={1280}>1280px</option>
            <option value={1920}>1920px</option>
          </select>
        </label>
        <div className="flex flex-wrap items-center gap-4 text-sm">
          {(["autoplay", "loop", "muted"] as const).map((key) => (
            <label className="flex items-center gap-2" key={key}>
              <input
                checked={settings[key]}
                onChange={(event) =>
                  setSettings({ ...settings, [key]: event.target.checked })
                }
                type="checkbox"
              />
              {key === "autoplay"
                ? "Tự phát"
                : key === "loop"
                  ? "Lặp lại"
                  : "Tắt tiếng"}
            </label>
          ))}
        </div>
      </div>
      {settings.autoplay && !settings.muted ? (
        <p className="mt-2 text-xs text-red-700">
          Video tự phát phải tắt tiếng để hoạt động ổn định trên điện thoại.
        </p>
      ) : null}
      {error ? <p className="mt-2 text-xs text-red-700">{error}</p> : null}
      <Button
        className="mt-3"
        disabled={saving || (settings.autoplay && !settings.muted)}
        onClick={() => void save()}
        type="button"
      >
        {saving ? "Đang lưu…" : "Lưu cấu hình video"}
      </Button>
    </details>
  );
}

function PreviewPanel({
  data,
  loading,
  mode,
  onMode,
}: {
  data: Awaited<ReturnType<typeof publicWorkAdminApi.preview>> | undefined;
  loading: boolean;
  mode: "desktop" | "mobile";
  onMode: (mode: "desktop" | "mobile") => void;
}) {
  return (
    <div className="bg-neutral-100 p-5 sm:p-8">
      <div className="mb-5 flex items-center justify-between gap-3">
        <p className="text-sm font-bold text-neutral-700">
          Bản xem trước an toàn
        </p>
        <div className="flex rounded-xl border border-neutral-200 bg-white p-1">
          <button
            aria-label="Xem bản desktop"
            className={`rounded-lg p-2 ${mode === "desktop" ? "bg-neutral-950 text-white" : "text-neutral-500"}`}
            onClick={() => onMode("desktop")}
            type="button"
          >
            <Monitor className="size-4" />
          </button>
          <button
            aria-label="Xem bản mobile"
            className={`rounded-lg p-2 ${mode === "mobile" ? "bg-neutral-950 text-white" : "text-neutral-500"}`}
            onClick={() => onMode("mobile")}
            type="button"
          >
            <Smartphone className="size-4" />
          </button>
        </div>
      </div>
      <article
        className={`mx-auto overflow-hidden bg-white shadow-xl transition-all ${mode === "mobile" ? "max-w-[23rem] rounded-[2rem]" : "max-w-5xl rounded-2xl"}`}
      >
        {loading ? (
          <p className="p-8 text-sm text-neutral-500">
            Đang tạo bản xem trước…
          </p>
        ) : data ? (
          <>
            <div className="relative aspect-[16/8] bg-ink-950">
              {data.media.find((item) => item.isThumbnail)?.url ? (
                <Image
                  alt={
                    data.media.find((item) => item.isThumbnail)?.altText ??
                    data.title
                  }
                  className="object-cover opacity-80"
                  fill
                  sizes="(max-width: 768px) 100vw, 1024px"
                  src={data.media.find((item) => item.isThumbnail)?.url ?? ""}
                  unoptimized
                />
              ) : (
                <div className="grid size-full place-items-center text-sm text-neutral-400">
                  Chưa có ảnh đại diện sẵn sàng
                </div>
              )}
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-6 text-white">
                <p className="text-xs font-bold tracking-[0.2em] text-gold-300 uppercase">
                  {data.categoryName}
                </p>
                <h2 className="mt-2 text-2xl font-bold tracking-tight sm:text-4xl">
                  {data.title}
                </h2>
              </div>
            </div>
            <div className="p-6 sm:p-8">
              <p className="text-base leading-7 text-neutral-700">
                {data.shortDescription}
              </p>
              {data.fullDescription ? (
                <p className="mt-5 whitespace-pre-line text-sm leading-7 text-neutral-600">
                  {data.fullDescription}
                </p>
              ) : null}
              <p className="mt-6 border-t border-neutral-200 pt-4 text-sm font-bold">
                {data.authorDisplayName || "Tác giả chưa công bố"}
              </p>
            </div>
          </>
        ) : (
          <p className="p-8 text-sm text-red-700">
            Không thể tạo bản xem trước.
          </p>
        )}
      </article>
    </div>
  );
}

function ReasonDialog({
  action,
  isPending,
  onCancel,
  onConfirm,
  onReason,
  reason,
}: {
  action?: StateAction;
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  onReason: (value: string) => void;
  reason: string;
}) {
  if (action !== "suspend" && action !== "archive") return null;
  return (
    <div
      aria-labelledby="reason-dialog-title"
      aria-modal="true"
      className="fixed inset-0 z-50 grid place-items-center bg-ink-950/70 p-4 backdrop-blur-sm"
      role="dialog"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <ShieldAlert className="size-8 text-amber-700" />
        <h2 className="mt-4 text-xl font-bold" id="reason-dialog-title">
          {action === "suspend" ? "Tạm ngưng tác phẩm" : "Lưu trữ tác phẩm"}
        </h2>
        <p className="mt-2 text-sm leading-6 text-neutral-600">
          Lý do được lưu trong nhật ký kiểm toán và không hiển thị công khai.
        </p>
        <label className="mt-4 block text-sm font-bold">
          Lý do
          <textarea
            autoFocus
            className={`${fieldClass} mt-2 min-h-28 py-3`}
            maxLength={1000}
            onChange={(event) => onReason(event.target.value)}
            value={reason}
          />
        </label>
        <div className="mt-5 flex justify-end gap-2">
          <Button disabled={isPending} onClick={onCancel} variant="ghost">
            Quay lại
          </Button>
          <Button
            disabled={isPending || reason.trim().length < 3}
            onClick={onConfirm}
          >
            {isPending ? "Đang xử lý…" : "Xác nhận"}
          </Button>
        </div>
      </div>
    </div>
  );
}
