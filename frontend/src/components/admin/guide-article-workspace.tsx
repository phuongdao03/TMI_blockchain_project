"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpenText, CirclePlus, Eye, Search, Trash2 } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useMemo, useState } from "react";

import {
  guideAudienceLabel,
  guideCategoryLabel,
} from "@/components/guide/guide-center";
import { guideApi } from "@/lib/api/client";
import type {
  CmsGuideArticle,
  CmsGuideArticleInput,
  CmsGuideAudience,
  CmsGuideStatus,
} from "@/lib/api/types";

const AUDIENCES: CmsGuideAudience[] = [
  "PUBLIC",
  "VIEWER",
  "USER",
  "MODERATOR",
  "SUPER_ADMIN",
  "EMPLOYEE",
  "MEMBERSHIP_SILVER",
  "MEMBERSHIP_COMPANION",
  "MEMBERSHIP_PRESTIGE",
];
const EMPTY_ARTICLES: CmsGuideArticle[] = [];

const EMPTY_ARTICLE: CmsGuideArticleInput = {
  title: "",
  slug: "",
  summary: "",
  category: "getting-started",
  audiences: ["PUBLIC"],
  bodyHtml: "<h2>Bắt đầu</h2>\n<p>Viết các bước hướng dẫn tại đây.</p>",
  sortOrder: 0,
};

const STATUS_LABELS: Record<CmsGuideStatus, string> = {
  DRAFT: "Bản nháp",
  PUBLISHED: "Đã xuất bản",
  ARCHIVED: "Đã lưu trữ",
};

export function GuideArticleWorkspace() {
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [audience, setAudience] = useState<CmsGuideAudience | "">("");
  const [status, setStatus] = useState<CmsGuideStatus | "">("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<CmsGuideArticle | null>(null);
  const [form, setForm] = useState<CmsGuideArticleInput>(EMPTY_ARTICLE);
  const [showPreview, setShowPreview] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<CmsGuideArticle | null>(
    null,
  );
  const [message, setMessage] = useState("");

  const list = useQuery({
    queryKey: [
      "admin-guide-articles",
      search,
      category,
      audience,
      status,
      page,
    ],
    queryFn: () =>
      guideApi.adminList({
        page,
        pageSize: 20,
        query: search || undefined,
        category: category || undefined,
        audience: audience || undefined,
        status: status || undefined,
      }),
  });
  const invalidate = async () =>
    queryClient.invalidateQueries({ queryKey: ["admin-guide-articles"] });
  const save = useMutation({
    mutationFn: (input: CmsGuideArticleInput) =>
      selected ? guideApi.update(selected.id, input) : guideApi.create(input),
    onSuccess: async (article) => {
      setSelected(article);
      setForm(toInput(article));
      setShowPreview(false);
      setMessage("Đã lưu bài hướng dẫn.");
      await invalidate();
    },
    onError: () =>
      setMessage("Không lưu được bài viết. Kiểm tra đường dẫn và thử lại."),
  });
  const changeStatus = useMutation({
    mutationFn: ({
      id,
      nextStatus,
    }: {
      id: string;
      nextStatus: CmsGuideStatus;
    }) => guideApi.setStatus(id, nextStatus),
    onSuccess: async (article) => {
      setSelected(article);
      setForm(toInput(article));
      setMessage(`Trạng thái bài viết: ${STATUS_LABELS[article.status]}.`);
      await invalidate();
    },
    onError: () => setMessage("Không đổi được trạng thái bài viết."),
  });
  const remove = useMutation({
    mutationFn: (id: string) => guideApi.delete(id),
    onSuccess: async () => {
      setSelected(null);
      setForm(EMPTY_ARTICLE);
      setDeleteTarget(null);
      setMessage("Đã xóa bài hướng dẫn.");
      await invalidate();
    },
    onError: () =>
      setMessage("Không xóa được bài viết. Hãy lưu trữ bài đã xuất bản trước."),
  });

  const articles = list.data?.data ?? EMPTY_ARTICLES;
  const total = list.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / 20));
  const categories = useMemo(
    () => [...new Set(articles.map((article) => article.category))].sort(),
    [articles],
  );

  function searchArticles(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchDraft.trim());
    setPage(1);
  }

  function startNew() {
    setSelected(null);
    setForm({ ...EMPTY_ARTICLE, audiences: ["PUBLIC"] });
    setShowPreview(false);
    setMessage("");
  }

  function editArticle(article: CmsGuideArticle) {
    setSelected(article);
    setForm(toInput(article));
    setShowPreview(false);
    setMessage("");
  }

  function toggleAudience(value: CmsGuideAudience) {
    setForm((current) => {
      if (value === "PUBLIC") {
        return {
          ...current,
          audiences: current.audiences.includes("PUBLIC") ? [] : ["PUBLIC"],
        };
      }
      const withoutPublic = current.audiences.filter(
        (item) => item !== "PUBLIC",
      );
      return {
        ...current,
        audiences: withoutPublic.includes(value)
          ? withoutPublic.filter((item) => item !== value)
          : [...withoutPublic, value],
      };
    });
  }

  function submitArticle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    save.mutate({
      ...form,
      title: form.title.trim(),
      slug: form.slug.trim(),
      summary: form.summary.trim(),
      category: form.category.trim(),
      bodyHtml: form.bodyHtml.trim(),
    });
  }

  function changeFilter<T extends string>(
    setter: (value: T) => void,
    value: T,
  ) {
    setter(value);
    setPage(1);
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-10 text-neutral-900">
      <header className="flex flex-col gap-4 border-b border-neutral-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            <BookOpenText aria-hidden="true" className="size-4" /> Trung tâm
            hướng dẫn
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            Quản lý bài viết
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
            Soạn, xem trước, xuất bản và lưu trữ tài liệu theo đúng vai trò hoặc
            hồ sơ nhân viên đã liên kết.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            className="inline-flex min-h-11 items-center rounded-xl border border-neutral-300 bg-white px-4 text-sm font-bold hover:bg-neutral-50"
            href="/admin/guide"
          >
            Cẩm nang vận hành
          </Link>
          <button
            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary-700 px-4 text-sm font-bold text-white hover:bg-primary-800"
            onClick={startNew}
            type="button"
          >
            <CirclePlus aria-hidden="true" className="size-4" /> Bài viết mới
          </button>
        </div>
      </header>

      <section
        aria-label="Tìm và lọc bài viết"
        className="grid gap-3 rounded-2xl border border-neutral-200 bg-white p-4 sm:grid-cols-2 xl:grid-cols-5"
      >
        <form
          className="flex gap-2 sm:col-span-2 xl:col-span-2"
          onSubmit={searchArticles}
        >
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">Tìm bài viết</span>
            <Search
              aria-hidden="true"
              className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400"
            />
            <input
              className="min-h-11 w-full rounded-lg border border-neutral-300 pl-9 pr-3 text-sm outline-none focus:border-primary-700"
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="Tiêu đề, tóm tắt hoặc đường dẫn"
              value={searchDraft}
            />
          </label>
          <button
            className="min-h-11 rounded-lg border border-neutral-300 px-3 text-sm font-semibold hover:bg-neutral-50"
            type="submit"
          >
            Tìm
          </button>
        </form>
        <label className="grid gap-1 text-xs font-bold text-neutral-600">
          Chủ đề
          <select
            className="min-h-11 rounded-lg border border-neutral-300 bg-white px-3 text-sm font-normal text-neutral-900"
            onChange={(event) => changeFilter(setCategory, event.target.value)}
            value={category}
          >
            <option value="">Tất cả</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {guideCategoryLabel(item)}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-xs font-bold text-neutral-600">
          Đối tượng
          <select
            className="min-h-11 rounded-lg border border-neutral-300 bg-white px-3 text-sm font-normal text-neutral-900"
            onChange={(event) =>
              changeFilter(
                setAudience,
                event.target.value as CmsGuideAudience | "",
              )
            }
            value={audience}
          >
            <option value="">Tất cả</option>
            {AUDIENCES.map((item) => (
              <option key={item} value={item}>
                {guideAudienceLabel(item)}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-xs font-bold text-neutral-600">
          Trạng thái
          <select
            className="min-h-11 rounded-lg border border-neutral-300 bg-white px-3 text-sm font-normal text-neutral-900"
            onChange={(event) =>
              changeFilter(setStatus, event.target.value as CmsGuideStatus | "")
            }
            value={status}
          >
            <option value="">Tất cả</option>
            {Object.entries(STATUS_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(18rem,0.85fr)_minmax(0,1.35fr)]">
        <section aria-labelledby="guide-articles-heading" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold" id="guide-articles-heading">
              Bài viết ({total})
            </h2>
            {list.isFetching && (
              <span aria-live="polite" className="text-xs text-neutral-500">
                Đang cập nhật…
              </span>
            )}
          </div>
          {list.isPending && (
            <p
              aria-live="polite"
              className="rounded-xl border border-neutral-200 p-5 text-sm text-neutral-500"
            >
              Đang tải bài viết…
            </p>
          )}
          {list.isError && (
            <p
              className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-800"
              role="alert"
            >
              Không tải được danh sách bài viết.
            </p>
          )}
          {!list.isPending && !list.isError && articles.length === 0 && (
            <div className="rounded-2xl border border-dashed border-neutral-300 p-8 text-center">
              <p className="font-semibold">Chưa có bài viết phù hợp</p>
              <p className="mt-1 text-sm text-neutral-500">
                Tạo bài mới hoặc điều chỉnh bộ lọc.
              </p>
            </div>
          )}
          <ul className="space-y-3">
            {articles.map((article) => (
              <li key={article.id}>
                <button
                  className={`w-full rounded-2xl border bg-white p-4 text-left transition hover:border-primary-500 hover:shadow-sm ${selected?.id === article.id ? "border-primary-700 ring-1 ring-primary-700" : "border-neutral-200"}`}
                  onClick={() => editArticle(article)}
                  type="button"
                >
                  <span className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-bold text-primary-700">
                      {guideCategoryLabel(article.category)}
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${statusColor(article.status)}`}
                    >
                      {STATUS_LABELS[article.status]}
                    </span>
                  </span>
                  <span className="mt-2 block font-bold leading-6">
                    {article.title}
                  </span>
                  <span className="mt-1 block line-clamp-2 text-sm leading-5 text-neutral-600">
                    {article.summary}
                  </span>
                  <span className="mt-3 flex flex-wrap gap-1.5">
                    {article.audiences.map((item) => (
                      <span
                        className="rounded-full bg-neutral-100 px-2 py-1 text-[10px] font-semibold text-neutral-700"
                        key={item}
                      >
                        {guideAudienceLabel(item)}
                      </span>
                    ))}
                  </span>
                  <span className="mt-3 block text-xs text-neutral-500">
                    Bản {article.version} · Cập nhật{" "}
                    {formatDate(article.updatedAt)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {pageCount > 1 && (
            <nav
              aria-label="Phân trang bài viết"
              className="flex items-center justify-center gap-3 py-2"
            >
              <button
                className="min-h-10 rounded-lg border border-neutral-300 px-3 text-sm disabled:opacity-40"
                disabled={page <= 1}
                onClick={() => setPage((value) => value - 1)}
                type="button"
              >
                Trước
              </button>
              <span aria-live="polite" className="text-xs text-neutral-500">
                {page} / {pageCount}
              </span>
              <button
                className="min-h-10 rounded-lg border border-neutral-300 px-3 text-sm disabled:opacity-40"
                disabled={page >= pageCount}
                onClick={() => setPage((value) => value + 1)}
                type="button"
              >
                Tiếp
              </button>
            </nav>
          )}
        </section>

        <section
          aria-labelledby="guide-editor-heading"
          className="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-primary-700">
                {selected ? STATUS_LABELS[selected.status] : "Bản nháp mới"}
              </p>
              <h2 className="mt-1 text-xl font-bold" id="guide-editor-heading">
                {selected ? "Chỉnh sửa bài viết" : "Soạn bài viết"}
              </h2>
            </div>
            {selected?.status === "PUBLISHED" &&
              selected.audiences.includes("PUBLIC") && (
                <Link
                  className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-semibold hover:bg-neutral-50"
                  href={`/guide/${selected.slug}`}
                  target="_blank"
                >
                  <Eye aria-hidden="true" className="size-4" /> Xem công khai
                </Link>
              )}
            {selected?.audiences.includes("PUBLIC") && (
              <a
                className="inline-flex min-h-10 items-center text-sm font-semibold text-primary-700 underline-offset-4 hover:underline"
                href="#guide-feedback"
              >
                Xem phản hồi
              </a>
            )}
          </div>
          <form className="mt-5 space-y-4" onSubmit={submitArticle}>
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField
                label="Tiêu đề"
                maxLength={255}
                onChange={(title) =>
                  setForm((current) => ({ ...current, title }))
                }
                required
                value={form.title}
              />
              <TextField
                label="Đường dẫn"
                maxLength={180}
                onChange={(slug) =>
                  setForm((current) => ({ ...current, slug }))
                }
                pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
                required
                value={form.slug}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField
                label="Chủ đề (mã)"
                maxLength={80}
                onChange={(categoryValue) =>
                  setForm((current) => ({
                    ...current,
                    category: categoryValue,
                  }))
                }
                pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
                required
                value={form.category}
              />
              <TextField
                label="Thứ tự sắp xếp"
                min={0}
                onChange={(value) =>
                  setForm((current) => ({
                    ...current,
                    sortOrder: Number(value) || 0,
                  }))
                }
                type="number"
                value={String(form.sortOrder)}
              />
            </div>
            <label className="block text-sm font-semibold">
              Tóm tắt
              <textarea
                className="mt-1.5 min-h-20 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-normal outline-none focus:border-primary-700"
                maxLength={500}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    summary: event.target.value,
                  }))
                }
                required
                value={form.summary}
              />
            </label>
            <fieldset className="rounded-xl border border-neutral-200 p-3">
              <legend className="px-1 text-sm font-semibold">
                Ai có thể xem?
              </legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {AUDIENCES.map((item) => {
                  const checked = form.audiences.includes(item);
                  const disabled =
                    item === "PUBLIC"
                      ? form.audiences.some((value) => value !== "PUBLIC")
                      : form.audiences.includes("PUBLIC");
                  return (
                    <label
                      className={`flex min-h-10 items-center gap-2 rounded-lg px-2 text-sm ${disabled ? "text-neutral-400" : "text-neutral-800"}`}
                      key={item}
                    >
                      <input
                        checked={checked}
                        disabled={disabled}
                        onChange={() => toggleAudience(item)}
                        type="checkbox"
                      />
                      {guideAudienceLabel(item)}
                    </label>
                  );
                })}
              </div>
              <p className="mt-2 text-xs leading-5 text-neutral-500">
                “Nhân viên” là trạng thái liên kết hồ sơ, không phải vai trò.
                Bài công khai được chọn độc lập.
              </p>
            </fieldset>
            <label className="block text-sm font-semibold">
              Nội dung HTML
              <textarea
                className="mt-1.5 min-h-64 w-full rounded-lg border border-neutral-300 px-3 py-2 font-mono text-xs leading-6 outline-none focus:border-primary-700"
                maxLength={100_000}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    bodyHtml: event.target.value,
                  }))
                }
                required
                value={form.bodyHtml}
              />
            </label>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <button
                className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-semibold hover:bg-neutral-50"
                onClick={() => setShowPreview((value) => !value)}
                type="button"
              >
                <Eye aria-hidden="true" className="size-4" />{" "}
                {showPreview ? "Ẩn xem trước" : "Xem trước an toàn"}
              </button>
              <span className="text-xs text-neutral-500">
                Nội dung được làm sạch trước khi lưu.
              </span>
            </div>
            {showPreview && (
              <div
                aria-label="Xem trước an toàn"
                className="rounded-xl border border-neutral-200 bg-neutral-50 p-4"
              >
                <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
                  Bản xem trước
                </p>
                <h3 className="mt-2 text-lg font-bold">
                  {form.title || "Tiêu đề bài viết"}
                </h3>
                <p className="mt-1 text-sm text-neutral-600">
                  {form.summary || "Tóm tắt bài viết"}
                </p>
                <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-white p-3 font-mono text-xs leading-5 text-neutral-700">
                  {form.bodyHtml}
                </pre>
                <p className="mt-2 text-xs text-neutral-500">
                  Mã HTML hiển thị dưới dạng văn bản để không chạy script trong
                  bản nháp.
                </p>
              </div>
            )}
            {message && (
              <p
                aria-live="polite"
                className={`text-sm ${message.startsWith("Không") ? "text-red-700" : "text-green-700"}`}
                role={message.startsWith("Không") ? "alert" : "status"}
              >
                {message}
              </p>
            )}
            <div className="flex flex-wrap gap-2 border-t border-neutral-200 pt-4">
              <button
                className="min-h-11 rounded-lg bg-primary-700 px-4 text-sm font-bold text-white hover:bg-primary-800 disabled:opacity-50"
                disabled={save.isPending || form.audiences.length === 0}
                type="submit"
              >
                {save.isPending
                  ? "Đang lưu…"
                  : selected
                    ? "Lưu thay đổi"
                    : "Lưu bản nháp"}
              </button>
              {selected && (
                <LifecycleActions
                  article={selected}
                  changeStatus={(nextStatus) =>
                    changeStatus.mutate({ id: selected.id, nextStatus })
                  }
                  onDelete={() => setDeleteTarget(selected)}
                  busy={changeStatus.isPending || remove.isPending}
                />
              )}
            </div>
            {selected && (
              <p className="text-xs leading-5 text-neutral-500">
                Tạo {formatDate(selected.createdAt)} · Cập nhật{" "}
                {formatDate(selected.updatedAt)} · Lịch sử người chỉnh sửa được
                ghi trong nhật ký CMS.
              </p>
            )}
          </form>
          {selected?.audiences.includes("PUBLIC") && (
            <GuideFeedbackInbox articleId={selected.id} />
          )}
        </section>
      </div>

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <section
            aria-labelledby="delete-guide-heading"
            aria-modal="true"
            className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
            role="alertdialog"
          >
            <h2 className="text-lg font-bold" id="delete-guide-heading">
              Xóa bài hướng dẫn?
            </h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              Bài “{deleteTarget.title}” và các phản hồi gắn với bài sẽ bị xóa.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                className="min-h-10 rounded-lg border border-neutral-300 px-4 text-sm font-semibold"
                onClick={() => setDeleteTarget(null)}
                type="button"
              >
                Hủy
              </button>
              <button
                className="min-h-10 rounded-lg bg-red-700 px-4 text-sm font-bold text-white disabled:opacity-50"
                disabled={remove.isPending}
                onClick={() => remove.mutate(deleteTarget.id)}
                type="button"
              >
                {remove.isPending ? "Đang xóa…" : "Xóa bài"}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function GuideFeedbackInbox({ articleId }: { articleId: string }) {
  const [page, setPage] = useState(1);
  const feedback = useQuery({
    queryKey: ["admin-guide-feedback", articleId, page],
    queryFn: () => guideApi.adminFeedback(articleId, page),
  });
  const rows = feedback.data?.data ?? [];
  const total = feedback.data?.meta.total ?? 0;
  return (
    <section
      aria-label="Phản hồi về bài hướng dẫn"
      className="mt-8 scroll-mt-24 border-t border-neutral-200 pt-6"
      id="guide-feedback"
    >
      <h3 className="text-lg font-semibold">Phản hồi từ người đọc ({total})</h3>
      <p className="mt-1 text-sm text-neutral-600">
        Góp ý cho bài này được lưu tại đây để ban quản trị nội dung xem và chỉnh
        sửa hướng dẫn.
      </p>
      {feedback.isPending && <p className="mt-4 text-sm">Đang tải phản hồi…</p>}
      {feedback.isError && (
        <p role="alert" className="mt-4 text-sm text-red-700">
          Chưa tải được phản hồi.
        </p>
      )}
      {!feedback.isPending && !feedback.isError && rows.length === 0 && (
        <p className="mt-4 text-sm text-neutral-600">Chưa có phản hồi.</p>
      )}
      {rows.length > 0 && (
        <ul className="mt-4 divide-y divide-neutral-200 border-y border-neutral-200">
          {rows.map((item) => (
            <li key={item.id} className="py-4 text-sm">
              <div className="flex items-center justify-between gap-2">
                <strong>{item.helpful ? "Hữu ích" : "Cần cải thiện"}</strong>
                <time
                  className="text-xs text-neutral-500"
                  dateTime={item.createdAt}
                >
                  {formatDate(item.createdAt)}
                </time>
              </div>
              {item.comment && (
                <p className="mt-2 whitespace-pre-wrap break-words text-neutral-700">
                  {item.comment}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
      {total > 20 && (
        <nav
          aria-label="Trang phản hồi"
          className="mt-3 flex items-center gap-3 text-sm"
        >
          <button
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            type="button"
          >
            Trước
          </button>
          <span>
            {page} / {Math.ceil(total / 20)}
          </span>
          <button
            disabled={page * 20 >= total}
            onClick={() => setPage(page + 1)}
            type="button"
          >
            Tiếp
          </button>
        </nav>
      )}
    </section>
  );
}

function LifecycleActions({
  article,
  changeStatus,
  onDelete,
  busy,
}: {
  article: CmsGuideArticle;
  changeStatus: (status: CmsGuideStatus) => void;
  onDelete: () => void;
  busy: boolean;
}) {
  const statusTarget: CmsGuideStatus =
    article.status === "PUBLISHED" ? "ARCHIVED" : "PUBLISHED";
  return (
    <>
      <button
        className="min-h-11 rounded-lg border border-neutral-300 px-4 text-sm font-semibold hover:bg-neutral-50 disabled:opacity-50"
        disabled={busy}
        onClick={() => changeStatus(statusTarget)}
        type="button"
      >
        {article.status === "PUBLISHED" ? "Lưu trữ" : "Xuất bản"}
      </button>
      {article.status !== "DRAFT" && (
        <button
          className="min-h-11 rounded-lg border border-neutral-300 px-4 text-sm font-semibold hover:bg-neutral-50 disabled:opacity-50"
          disabled={busy}
          onClick={() => changeStatus("DRAFT")}
          type="button"
        >
          Chuyển về bản nháp
        </button>
      )}
      {article.status !== "PUBLISHED" ? (
        <button
          aria-label="Xóa bài viết"
          className="grid size-11 place-items-center rounded-lg border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-50"
          disabled={busy}
          onClick={onDelete}
          type="button"
        >
          <Trash2 aria-hidden="true" className="size-4" />
        </button>
      ) : (
        <span className="self-center text-xs text-neutral-500">
          Lưu trữ trước khi xóa.
        </span>
      )}
    </>
  );
}

function TextField({
  label,
  onChange,
  ...props
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  maxLength?: number;
  pattern?: string;
  required?: boolean;
  min?: number;
  type?: "text" | "number";
}) {
  const id = `guide-field-${label.toLocaleLowerCase("vi").replace(/[^a-z0-9]+/g, "-")}`;
  return (
    <label className="block text-sm font-semibold" htmlFor={id}>
      {label}
      <input
        className="mt-1.5 min-h-11 w-full rounded-lg border border-neutral-300 px-3 text-sm font-normal outline-none focus:border-primary-700"
        id={id}
        onChange={(event) => onChange(event.target.value)}
        {...props}
      />
    </label>
  );
}

function toInput(article: CmsGuideArticle): CmsGuideArticleInput {
  return {
    title: article.title,
    slug: article.slug,
    summary: article.summary,
    category: article.category,
    audiences: [...article.audiences],
    bodyHtml: article.bodyHtml,
    sortOrder: article.sortOrder,
  };
}

function statusColor(status: CmsGuideStatus): string {
  if (status === "PUBLISHED") return "bg-green-100 text-green-800";
  if (status === "ARCHIVED") return "bg-neutral-200 text-neutral-700";
  return "bg-amber-100 text-amber-800";
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? "gần đây"
    : new Intl.DateTimeFormat("vi-VN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      }).format(date);
}
