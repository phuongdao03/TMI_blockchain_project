"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Bold, Heading2, Italic, Link2 as LinkIcon, List, ListOrdered, LoaderCircle, Quote, Redo2, Save, Send, Undo2, Eye, Pencil } from "lucide-react";
import Link from "next/link";
import { startTransition, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { CommunityMarkdown } from "@/components/community/community-markdown";
import { CommunityPostImages } from "@/components/community/community-post-images";
import { FileUploader } from "@/components/media/file-uploader";
import { communityApi, communityMemberApi, publicApi } from "@/lib/api/client";
import { communityPostImageLimits } from "@/lib/media/upload";
import type {
  CommunityPostInput,
  CommunityRelatedWork,
  CommunityPostWriteResult,
} from "@/lib/api/types";

export function CommunityPostEditor({
  postId,
  relatedWork: initialRelatedWork,
}: {
  postId?: string;
  relatedWork?: CommunityRelatedWork | null;
}) {
  const categories = useQuery({
    queryKey: ["community", "categories"],
    queryFn: ({ signal }) => communityApi.categories(signal),
    staleTime: 5 * 60_000,
  });
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [relatedWorkSearch, setRelatedWorkSearch] = useState("");
  const [relatedWorkQuery, setRelatedWorkQuery] = useState("");
  const [relatedWork, setRelatedWork] = useState<CommunityRelatedWork | null>(initialRelatedWork ?? null);
  const [imageMediaIds, setImageMediaIds] = useState<string[]>([]);
  const [hasQueuedImages, setHasQueuedImages] = useState(false);
  const [uploaderSession, setUploaderSession] = useState(0);
  const [draft, setDraft] = useState<CommunityPostWriteResult | null>(null);
  const [savedInput, setSavedInput] = useState<CommunityPostInput | null>(null);
  const [busy, setBusy] = useState<"save" | "submit" | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [previewMode, setPreviewMode] = useState(false);
  const [ownerLoadApplied, setOwnerLoadApplied] = useState(false);
  const [canEditLoadedPost, setCanEditLoadedPost] = useState(true);
  const [autoSaveStatus, setAutoSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [autoSaveRevision, setAutoSaveRevision] = useState(0);
  const [historyCursor, setHistoryCursor] = useState({ index: 0, length: 1 });
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const autoSavePromiseRef = useRef<Promise<void> | null>(null);
  const lastAutoSaveAttemptRef = useRef<string | null>(null);
  const historyRef = useRef({ values: [""], index: 0 });
  const ownerPost = useQuery({
    queryKey: ["community", "mine", "post", postId],
    queryFn: ({ signal }) => communityMemberApi.myPost(postId!, signal),
    enabled: Boolean(postId),
    retry: false,
  });
  useEffect(() => {
    if (!ownerPost.data || ownerLoadApplied) return;
    startTransition(() => {
      const loaded = ownerPost.data!;
      setCanEditLoadedPost(loaded.status === "DRAFT" || loaded.status === "REJECTED");
      setTitle(loaded.title);
      setContent(loaded.content);
      setCategoryId(loaded.category.id);
      setTags(loaded.tags.map((tag) => tag.name));
      setRelatedWork(loaded.relatedWork);
      setImageMediaIds(loaded.images.map((image) => image.id));
      setDraft(loaded);
      lastAutoSaveAttemptRef.current = null;
      setSavedInput(snapshotInput({
        title: loaded.title,
        content: loaded.content,
        categoryId: loaded.category.id,
        tags: loaded.tags.map((tag) => tag.name),
        relatedWorkId: loaded.relatedWork?.id ?? null,
        imageMediaIds: loaded.images.map((image) => image.id),
      }));
      historyRef.current = { values: [loaded.content], index: 0 };
      setHistoryCursor({ index: 0, length: 1 });
      setOwnerLoadApplied(true);
    });
  }, [ownerPost.data, ownerLoadApplied]);
  const relatedWorks = useQuery({
    queryKey: ["community", "public-work-search", relatedWorkQuery],
    queryFn: () => publicApi.works({
      query: relatedWorkQuery,
      page: 1,
      pageSize: 6,
      sort: "newest",
    }),
    enabled: relatedWorkQuery.length >= 2,
  });
  const input = useMemo<CommunityPostInput>(() => ({
    title: title.trim(),
    content: content.trim(),
    categoryId,
    ...(tags.length ? { tags } : {}),
    relatedWorkId: relatedWork?.id ?? null,
    imageMediaIds,
  }), [categoryId, content, imageMediaIds, relatedWork?.id, tags, title]);
  const valid = Boolean(input.title && input.content && input.categoryId);
  const changedSinceSave = !sameInput(input, savedInput);
  const submitted = draft?.status === "PENDING";
  const ownerLoading = Boolean(postId) && !ownerLoadApplied && ownerPost.isPending;
  const ownerNotFoundOrFailed = Boolean(postId) && ownerPost.isError;

  function setEditorContent(next: string) {
    const history = historyRef.current;
    const values = history.values.slice(0, history.index + 1);
    if (values.at(-1) !== next) values.push(next);
    const bounded = values.slice(-100);
    historyRef.current = { values: bounded, index: bounded.length - 1 };
    setHistoryCursor({ index: bounded.length - 1, length: bounded.length });
    setContent(next);
  }

  function moveEditorHistory(direction: -1 | 1) {
    const history = historyRef.current;
    const index = Math.max(0, Math.min(history.values.length - 1, history.index + direction));
    historyRef.current = { ...history, index };
    setHistoryCursor({ index, length: history.values.length });
    setContent(history.values[index] ?? "");
  }

  function formatSelection(kind: "heading" | "bold" | "italic" | "bullet" | "numbered" | "quote" | "link") {
    const editor = editorRef.current;
    const start = editor?.selectionStart ?? content.length;
    const end = editor?.selectionEnd ?? start;
    const selected = content.slice(start, end);
    let replacement = selected || "văn bản";
    if (kind === "heading") replacement = `## ${selected || "Tiêu đề"}`;
    if (kind === "bold") replacement = `**${replacement}**`;
    if (kind === "italic") replacement = `*${replacement}*`;
    if (kind === "bullet") replacement = (selected || "Mục danh sách").split("\n").map((line) => `- ${line}`).join("\n");
    if (kind === "numbered") replacement = (selected || "Mục danh sách").split("\n").map((line, index) => `${index + 1}. ${line}`).join("\n");
    if (kind === "quote") replacement = (selected || "Trích dẫn").split("\n").map((line) => `> ${line}`).join("\n");
    if (kind === "link") replacement = `[${selected || "văn bản liên kết"}](/)`;
    const next = `${content.slice(0, start)}${replacement}${content.slice(end)}`;
    setEditorContent(next);
    requestAnimationFrame(() => {
      editorRef.current?.focus();
      editorRef.current?.setSelectionRange(start + replacement.length, start + replacement.length);
    });
  }

  function addTag() {
    const tag = tagInput.trim().replace(/\s+/g, " ");
    if (!tag || tag.length > 40 || tags.some((existing) => existing.toLocaleLowerCase() === tag.toLocaleLowerCase()) || tags.length >= 10) return;
    setTags((current) => [...current, tag]);
    setTagInput("");
  }

  async function persistDraft(): Promise<CommunityPostWriteResult> {
    if (draft) {
      if (changedSinceSave) {
        const updated = await communityApi.updatePost(draft.id, input);
        setDraft(updated);
        setImageMediaIds(updated.images.map((image) => image.id));
        setSavedInput(snapshotInput(input));
        return updated;
      }
      return draft;
    }
    const created = await communityApi.createPost(input);
    setDraft(created);
    setImageMediaIds(created.images.map((image) => image.id));
    setSavedInput(snapshotInput(input));
    return created;
  }

  useEffect(() => {
    if (
      !valid || !changedSinceSave || busy || hasQueuedImages || submitted ||
      !canEditLoadedPost || (postId && !ownerLoadApplied)
    ) return;
    const snapshot = snapshotInput(input);
    const attemptKey = JSON.stringify(snapshot);
    if (lastAutoSaveAttemptRef.current === attemptKey) return;
    const timer = window.setTimeout(() => {
      if (autoSavePromiseRef.current) return;
      lastAutoSaveAttemptRef.current = attemptKey;
      setAutoSaveStatus("saving");
      const pending = (async () => {
        try {
          const saved = draft
            ? await communityApi.updatePost(draft.id, snapshot)
            : await communityApi.createPost(snapshot);
          setDraft(saved);
          setImageMediaIds(saved.images.map((image) => image.id));
          setSavedInput(snapshot);
          setAutoSaveStatus("saved");
        } catch {
          setAutoSaveStatus("error");
        } finally {
          autoSavePromiseRef.current = null;
          setAutoSaveRevision((revision) => revision + 1);
        }
      })();
      autoSavePromiseRef.current = pending;
    }, COMMUNITY_AUTO_SAVE_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [
    autoSaveRevision,
    busy,
    canEditLoadedPost,
    changedSinceSave,
    draft,
    hasQueuedImages,
    input,
    ownerLoadApplied,
    postId,
    submitted,
    valid,
  ]);

  async function saveDraft() {
    await runAction("save");
  }

  async function submitForReview() {
    await runAction("submit");
  }

  function searchRelatedWorks() {
    const query = relatedWorkSearch.trim();
    if (query.length >= 2) setRelatedWorkQuery(query);
  }

  async function runAction(action: "save" | "submit") {
    if (!valid || busy || submitted) return;
    setBusy(action);
    setError("");
    setNotice("");
    try {
      const saved = await persistDraft();
      if (action === "save") {
        setNotice("Bản nháp đã được lưu.");
        return;
      }
      await communityApi.submitPost(saved.id);
      setDraft({ ...saved, status: "PENDING" });
      setNotice("Bài viết đã được gửi để kiểm duyệt.");
    } catch (actionError) {
      setError(getErrorMessage(actionError));
    } finally {
      setBusy(null);
    }
  }

  function startAnotherPost() {
    setTitle("");
    setContent("");
    setTags([]);
    setTagInput("");
    setCategoryId("");
    setRelatedWorkSearch("");
    setRelatedWorkQuery("");
    setRelatedWork(null);
    setImageMediaIds([]);
    setHasQueuedImages(false);
    setUploaderSession((current) => current + 1);
    setDraft(null);
    autoSavePromiseRef.current = null;
    lastAutoSaveAttemptRef.current = null;
    setAutoSaveStatus("idle");
    setSavedInput(null);
    setOwnerLoadApplied(false);
    historyRef.current = { values: [""], index: 0 };
    setHistoryCursor({ index: 0, length: 1 });
    setNotice("");
    setError("");
  }

  return (
    <div className="public-theme-surface min-h-[calc(100dvh-5rem)]">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8 lg:py-16">
        <Link
          className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-[var(--theme-muted)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--theme-accent)]"
          href="/community"
        >
          <ArrowLeft aria-hidden="true" className="size-4" /> Về cộng đồng
        </Link>
        <header className="mt-6 border-b border-[var(--theme-border)] pb-6 sm:mt-8 sm:pb-8">
          <p className="text-xs font-bold tracking-[0.18em] text-[var(--theme-accent)] uppercase">
            Chia sẻ cùng cộng đồng
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-[-0.035em] text-[var(--theme-text)] sm:text-4xl">
            {postId ? "Chỉnh sửa bài viết" : "Viết bài mới"}
          </h1>
          <p className="mt-3 text-sm leading-6 text-[var(--theme-muted)] sm:text-base">
            Bài viết được lưu nháp trước và chỉ xuất hiện sau khi được kiểm duyệt.
          </p>
        </header>

        {notice ? (
          <div
            className="mt-6 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 text-sm font-semibold text-[var(--theme-text)]"
            role="status"
          >
            <p>{notice}</p>
            {submitted ? (
              <div className="mt-3 flex flex-wrap gap-3">
                <Link
                  className="inline-flex min-h-10 items-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                  href="/community"
                >
                  Về cộng đồng
                </Link>
                <button
                  className="inline-flex min-h-10 items-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                  onClick={startAnotherPost}
                  type="button"
                >
                  Viết bài khác
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
        {error ? (
          <p
            className="mt-6 rounded-xl border border-red-300 bg-red-50 p-4 text-sm font-semibold text-red-900"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        {ownerLoading ? (
          <p aria-busy="true" className="mt-7 flex items-center gap-2 text-sm text-[var(--theme-muted)]" role="status">
            <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />Đang tải bài viết của bạn…
          </p>
        ) : null}
        {ownerNotFoundOrFailed ? (
          <div className="mt-7 rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-900" role="alert">
            Không thể tải bài viết để chỉnh sửa. Bài viết có thể không thuộc về bạn hoặc đã bị xóa.
            <Link className="ml-2 font-bold underline" href="/community/mine">Quay lại bài viết của tôi</Link>
          </div>
        ) : null}
        {postId && ownerLoadApplied && !canEditLoadedPost ? (
          <p className="mt-7 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 text-sm leading-6 text-[var(--theme-muted)]" role="status">
            Bài viết này đang chờ kiểm duyệt hoặc đã xuất bản nên chỉ có thể xem. <Link className="font-bold text-[var(--theme-accent)] underline" href="/community/mine">Quay lại bài viết của tôi</Link>
          </p>
        ) : null}

        {categories.isPending ? (
          <p aria-busy="true" className="mt-7 flex items-center gap-2 text-sm text-[var(--theme-muted)]" role="status">
            <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
            Đang tải chuyên mục…
          </p>
        ) : null}
        {categories.isError ? (
          <div className="mt-7 rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-900" role="alert">
            Không thể tải chuyên mục. Vui lòng tải lại trang.
          </div>
        ) : null}
        {categories.data?.length === 0 ? (
          <p className="mt-7 rounded-xl border border-[var(--theme-border)] p-4 text-sm text-[var(--theme-muted)]" role="status">
            Hiện chưa có chuyên mục để đăng bài.
          </p>
        ) : null}

        {categories.data?.length && !ownerLoading && !ownerNotFoundOrFailed ? (
          <form
            className="mt-7 space-y-6"
            onSubmit={(event) => {
              event.preventDefault();
              void submitForReview();
            }}
          >
            <label
              className="block text-sm font-semibold text-[var(--theme-text)]"
              htmlFor="community-post-category"
            >
              Chuyên mục
              <select
                className={controlClass}
                disabled={busy !== null || submitted || !canEditLoadedPost}
                id="community-post-category"
                onChange={(event) => setCategoryId(event.target.value)}
                required
                value={categoryId}
              >
                <option value="">Chọn chuyên mục</option>
                {categories.data.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label
              className="block text-sm font-semibold text-[var(--theme-text)]"
              htmlFor="community-post-title"
            >
              Tiêu đề
              <input
                autoComplete="off"
                className={controlClass}
                disabled={busy !== null || submitted || !canEditLoadedPost}
                id="community-post-title"
                onChange={(event) => setTitle(event.target.value)}
                required
                type="text"
                value={title}
              />
            </label>
            <div>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <label className="block text-sm font-semibold text-[var(--theme-text)]" htmlFor="community-post-content">Nội dung</label>
                <div aria-label="Chế độ nội dung" className="inline-flex rounded-lg border border-[var(--theme-border)] p-1" role="group">
                  <button aria-pressed={!previewMode} className="inline-flex min-h-9 items-center gap-2 rounded-md px-3 text-sm font-semibold text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]" disabled={!canEditLoadedPost} onClick={() => setPreviewMode(false)} type="button"><Pencil aria-hidden="true" className="size-4" />Soạn thảo</button>
                  <button aria-pressed={previewMode} className="inline-flex min-h-9 items-center gap-2 rounded-md px-3 text-sm font-semibold text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]" onClick={() => setPreviewMode(true)} type="button"><Eye aria-hidden="true" className="size-4" />Xem trước</button>
                </div>
              </div>
              {!previewMode ? (
                <>
                  <div aria-label="Định dạng Markdown" className="mt-2 flex flex-wrap gap-1 rounded-t-xl border border-b-0 border-[var(--theme-border)] bg-[var(--theme-elevated)] p-2" role="toolbar">
                    <ToolbarButton label="Tiêu đề cấp 2" onClick={() => formatSelection("heading")}><Heading2 aria-hidden="true" className="size-4" /></ToolbarButton>
                    <ToolbarButton label="In đậm" onClick={() => formatSelection("bold")}><Bold aria-hidden="true" className="size-4" /></ToolbarButton>
                    <ToolbarButton label="In nghiêng" onClick={() => formatSelection("italic")}><Italic aria-hidden="true" className="size-4" /></ToolbarButton>
                    <ToolbarButton label="Danh sách" onClick={() => formatSelection("bullet")}><List aria-hidden="true" className="size-4" /></ToolbarButton>
                    <ToolbarButton label="Danh sách có thứ tự" onClick={() => formatSelection("numbered")}><ListOrdered aria-hidden="true" className="size-4" /></ToolbarButton>
                    <ToolbarButton label="Trích dẫn" onClick={() => formatSelection("quote")}><Quote aria-hidden="true" className="size-4" /></ToolbarButton>
                    <ToolbarButton label="Chèn liên kết nội bộ" onClick={() => formatSelection("link")}><LinkIcon aria-hidden="true" className="size-4" /></ToolbarButton>
                    <ToolbarButton disabled={historyCursor.index <= 0} label="Hoàn tác" onClick={() => moveEditorHistory(-1)}><Undo2 aria-hidden="true" className="size-4" /></ToolbarButton>
                    <ToolbarButton disabled={historyCursor.index >= historyCursor.length - 1} label="Làm lại" onClick={() => moveEditorHistory(1)}><Redo2 aria-hidden="true" className="size-4" /></ToolbarButton>
                  </div>
                  <textarea
                    className={`${controlClass} mt-0 min-h-64 resize-y rounded-t-none py-3 leading-7`}
                    disabled={busy !== null || submitted || !canEditLoadedPost}
                    id="community-post-content"
                    aria-describedby="community-post-content-help"
                    onChange={(event) => setEditorContent(event.target.value)}
                    ref={editorRef}
                    required
                    value={content}
                  />
                </>
              ) : (
                <div aria-label="Bản xem trước nội dung" className="mt-2 min-h-64 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6" role="region">
                  {content.trim() ? <CommunityMarkdown content={content} /> : <p className="text-sm text-[var(--theme-muted)]">Nội dung xem trước sẽ hiển thị tại đây.</p>}
                </div>
              )}
              <span
                className="mt-2 block text-xs font-normal leading-5 text-[var(--theme-muted)]"
                id="community-post-content-help"
              >
                Có thể dùng cú pháp Markdown đơn giản. Thẻ HTML sẽ hiển thị như
                văn bản.
              </span>
            </div>
            <div>
              <label className="block text-sm font-semibold text-[var(--theme-text)]" htmlFor="community-post-tags">Thẻ chủ đề <span className="font-normal text-[var(--theme-muted)]">(tối đa 10)</span></label>
              <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                <input autoComplete="off" className={searchControlClass} disabled={busy !== null || submitted || !canEditLoadedPost || tags.length >= 10} id="community-post-tags" maxLength={40} onChange={(event) => setTagInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addTag(); } }} placeholder="Ví dụ: làng nghề" value={tagInput} />
                <button className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:opacity-50" disabled={!tagInput.trim() || tags.length >= 10 || busy !== null || submitted || !canEditLoadedPost} onClick={addTag} type="button">Thêm thẻ</button>
              </div>
              <ul aria-label="Thẻ đã chọn" className="mt-3 flex flex-wrap gap-2">
                {tags.map((tag) => <li className="inline-flex min-h-9 items-center gap-2 rounded-full border border-[var(--theme-border)] bg-[var(--theme-surface)] pl-3 pr-1 text-sm text-[var(--theme-text)]" key={tag}>{tag}<button aria-label={`Xóa thẻ ${tag}`} className="grid size-8 place-items-center rounded-full text-[var(--theme-muted)] hover:bg-[var(--theme-elevated)] focus-visible:outline-2 focus-visible:outline-[var(--theme-accent)] disabled:opacity-50" disabled={busy !== null || submitted || !canEditLoadedPost} onClick={() => setTags((current) => current.filter((item) => item !== tag))} type="button">×</button></li>)}
              </ul>
            </div>
            <section
              aria-labelledby="community-related-work-heading"
              className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5"
            >
              <h2
                className="text-sm font-bold text-[var(--theme-text)]"
                id="community-related-work-heading"
              >
                Tác phẩm liên quan <span className="font-normal text-[var(--theme-muted)]">(không bắt buộc)</span>
              </h2>
              <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
                Tìm trong danh mục tác phẩm đã xuất bản rồi chọn kết quả. Không nhập liên kết hoặc mã tác phẩm.
              </p>
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <label className="sr-only" htmlFor="community-related-work-search">
                  Tìm tác phẩm đã xuất bản
                </label>
                <input
                  autoComplete="off"
                  className={searchControlClass}
                disabled={busy !== null || submitted || !canEditLoadedPost}
                  id="community-related-work-search"
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      searchRelatedWorks();
                    }
                  }}
                  maxLength={120}
                  onChange={(event) => setRelatedWorkSearch(event.target.value)}
                  placeholder="Nhập tên tác phẩm"
                  type="search"
                  value={relatedWorkSearch}
                />
                <button
                  className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50"
                disabled={relatedWorkSearch.trim().length < 2 || busy !== null || submitted || !canEditLoadedPost}
                  onClick={searchRelatedWorks}
                  type="button"
                >
                  Tìm tác phẩm
                </button>
              </div>
              {relatedWork ? (
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--theme-border)] p-3">
                  <p className="text-sm text-[var(--theme-text)]" role="status">
                    Đã liên kết: <span className="font-semibold">{relatedWork.title}</span>
                  </p>
                  <button
                    className="min-h-10 rounded-lg px-3 text-sm font-semibold text-[var(--theme-muted)] underline underline-offset-4 hover:text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:opacity-50"
                    disabled={busy !== null || submitted || !canEditLoadedPost}
                    onClick={() => setRelatedWork(null)}
                    type="button"
                  >
                    Bỏ liên kết
                  </button>
                </div>
              ) : null}
              {relatedWorkQuery ? (
                <div aria-live="polite" className="mt-3">
                  {relatedWorks.isFetching ? (
                    <p className="text-sm text-[var(--theme-muted)]" role="status">Đang tìm tác phẩm công khai…</p>
                  ) : null}
                  {relatedWorks.isError ? (
                    <div className="flex flex-wrap items-center gap-3" role="alert">
                      <p className="text-sm text-red-800">Chưa thể tìm tác phẩm. Vui lòng thử lại.</p>
                      <button className="text-sm font-bold underline underline-offset-4" onClick={() => void relatedWorks.refetch()} type="button">Thử lại</button>
                    </div>
                  ) : null}
                  {relatedWorks.data?.data.length === 0 ? (
                    <p className="text-sm text-[var(--theme-muted)]" role="status">Không tìm thấy tác phẩm đã xuất bản phù hợp.</p>
                  ) : null}
                  {relatedWorks.data?.data.length ? (
                    <ul aria-label="Kết quả tác phẩm công khai" className="mt-2 divide-y divide-[var(--theme-border)] rounded-lg border border-[var(--theme-border)]">
                      {relatedWorks.data.data.map((work) => (
                        <li key={work.id}>
                          <button
                            aria-pressed={relatedWork?.id === work.id}
                            aria-label={`Chọn tác phẩm: ${work.title}`}
                            className="flex min-h-11 w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm font-semibold text-[var(--theme-text)] hover:bg-[var(--theme-elevated)] focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--theme-accent)] disabled:opacity-50"
                            disabled={busy !== null || submitted || !canEditLoadedPost}
                            onClick={() => setRelatedWork({ id: work.id, title: work.title, slug: work.slug })}
                            type="button"
                          >
                            <span className="break-words">{work.title}</span>
                            <span aria-hidden="true" className="shrink-0 text-xs text-[var(--theme-muted)]">{relatedWork?.id === work.id ? "Đã chọn" : "Chọn"}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
            </section>
            <section
              aria-labelledby="community-post-images-heading"
              className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5"
            >
              <h2
                className="text-sm font-bold text-[var(--theme-text)]"
                id="community-post-images-heading"
              >
                Ảnh đính kèm <span className="font-normal text-[var(--theme-muted)]">(không bắt buộc, tối đa {COMMUNITY_IMAGE_MAX_COUNT} ảnh)</span>
              </h2>
              <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
                Chọn JPEG, PNG hoặc WebP tối đa {(COMMUNITY_IMAGE_MAX_BYTES / 1_048_576).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} MB. Ảnh được kiểm tra an toàn trước khi đính kèm.
              </p>
              <div className="mt-4">
                <FileUploader
                  cleanupCompletedOnRemove
                  constraints={{
                    allowedMimeTypes: ["image/jpeg", "image/png", "image/webp"],
                    maxBytes: COMMUNITY_IMAGE_MAX_BYTES,
                  }}
                disabled={busy !== null || submitted || !canEditLoadedPost}
                  key={uploaderSession}
                  label="Ảnh bài viết"
                  maxFiles={Math.max(0, COMMUNITY_IMAGE_MAX_COUNT - imageMediaIds.length)}
                  multiple
                  onComplete={(asset) => {
                    setImageMediaIds((current) => {
                      if (current.includes(asset.id) || current.length >= COMMUNITY_IMAGE_MAX_COUNT) {
                        return current;
                      }
                      return [...current, asset.id];
                    });
                  }}
                  onQueueChange={setHasQueuedImages}
                  purpose="COMMUNITY_POST"
                />
              </div>
              {hasQueuedImages ? (
                <p className="mt-3 text-sm font-semibold text-[var(--theme-muted)]" role="status">
                  Tải xong và chờ kiểm tra ảnh trước khi lưu bài viết.
                </p>
              ) : null}
              {imageMediaIds.length ? (
                <ol
                  aria-label="Ảnh đã tải lên"
                  className="mt-4 divide-y divide-[var(--theme-border)] rounded-lg border border-[var(--theme-border)]"
                >
                  {imageMediaIds.map((mediaId, index) => (
                    <li
                      className="flex flex-wrap items-center gap-2 p-3"
                      key={mediaId}
                    >
                      <span className="min-w-0 flex-1 text-sm font-semibold text-[var(--theme-text)]">
                        Ảnh đã kiểm tra {index + 1}
                      </span>
                      <button
                        aria-label={`Đưa ảnh ${index + 1} lên trước`}
                        className="min-h-10 rounded-lg px-3 text-sm font-semibold text-[var(--theme-muted)] underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:opacity-50"
                        disabled={index === 0 || busy !== null || hasQueuedImages || submitted || !canEditLoadedPost}
                        onClick={() => setImageMediaIds((current) => reorderCommunityImages(current, index, -1))}
                        type="button"
                      >
                        Chuyển lên
                      </button>
                      <button
                        aria-label={`Đưa ảnh ${index + 1} xuống sau`}
                        className="min-h-10 rounded-lg px-3 text-sm font-semibold text-[var(--theme-muted)] underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:opacity-50"
                        disabled={index === imageMediaIds.length - 1 || busy !== null || hasQueuedImages || submitted || !canEditLoadedPost}
                        onClick={() => setImageMediaIds((current) => reorderCommunityImages(current, index, 1))}
                        type="button"
                      >
                        Chuyển xuống
                      </button>
                      <button
                        aria-label={`Xóa ảnh ${index + 1}`}
                        className="min-h-10 rounded-lg px-3 text-sm font-semibold text-red-700 underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:opacity-50"
                        disabled={busy !== null || hasQueuedImages || submitted || !canEditLoadedPost}
                        onClick={() => setImageMediaIds((current) => current.filter((id) => id !== mediaId))}
                        type="button"
                      >
                        Xóa
                      </button>
                    </li>
                  ))}
                </ol>
              ) : null}
              {draft?.status === "DRAFT" ? (
                <CommunityPostImages
                  images={imageMediaIds.flatMap((id) => {
                    const image = draft.images.find((item) => item.id === id);
                    return image ? [image] : [];
                  })}
                  postSlug={draft.slug}
                  postTitle={draft.title}
                />
              ) : null}
            </section>
            <div className="flex flex-col-reverse gap-3 border-t border-[var(--theme-border)] pt-5 sm:flex-row sm:justify-end">
              <p aria-live="polite" className="self-center text-sm text-[var(--theme-muted)]" role="status">
                {!valid ? "Nhập tiêu đề, nội dung và chuyên mục để bật tự lưu." : autoSaveStatus === "saving" ? "Đang tự lưu bản nháp…" : autoSaveStatus === "saved" ? "Bản nháp đã tự lưu." : autoSaveStatus === "error" ? "Chưa thể tự lưu. Hãy thử lại bằng nút lưu bản nháp." : changedSinceSave ? "Thay đổi sẽ tự lưu khi bạn tạm dừng nhập." : ""}
              </p>
              <button
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[var(--theme-border)] px-5 text-sm font-bold text-[var(--theme-text)] transition hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!valid || !changedSinceSave || busy !== null || autoSaveStatus === "saving" || hasQueuedImages || submitted || !canEditLoadedPost}
                onClick={() => void saveDraft()}
                type="button"
              >
                {busy === "save" ? (
                  <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
                ) : (
                  <Save aria-hidden="true" className="size-4" />
                )}
                Lưu bản nháp
              </button>
              <button
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[var(--theme-accent)] px-5 text-sm font-bold text-[var(--theme-accent-contrast)] transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!valid || busy !== null || autoSaveStatus === "saving" || hasQueuedImages || submitted || !canEditLoadedPost}
                type="submit"
              >
                {busy === "submit" ? (
                  <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
                ) : (
                  <Send aria-hidden="true" className="size-4" />
                )}
                Gửi duyệt
              </button>
            </div>
          </form>
        ) : null}
      </div>
    </div>
  );
}

const controlClass =
  "mt-2 min-h-12 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm font-normal text-[var(--theme-text)] outline-none transition focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20 disabled:cursor-not-allowed disabled:opacity-60";
const searchControlClass =
  "min-h-12 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm font-normal text-[var(--theme-text)] outline-none transition focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20 disabled:cursor-not-allowed disabled:opacity-60";
const COMMUNITY_IMAGE_MAX_COUNT = communityPostImageLimits.maxCount;
const COMMUNITY_IMAGE_MAX_BYTES = communityPostImageLimits.maxBytes;
const COMMUNITY_AUTO_SAVE_DELAY_MS = 1_200;

function sameInput(
  current: CommunityPostInput,
  saved: CommunityPostInput | null,
): boolean {
  return Boolean(
    saved &&
      current.title === saved.title &&
      current.content === saved.content &&
      current.categoryId === saved.categoryId &&
      current.relatedWorkId === saved.relatedWorkId &&
      sameStringList(current.tags ?? [], saved.tags ?? []) &&
      sameStringList(current.imageMediaIds ?? [], saved.imageMediaIds ?? []),
  );
}

function snapshotInput(input: CommunityPostInput): CommunityPostInput {
  return {
    ...input,
    tags: [...(input.tags ?? [])],
    imageMediaIds: [...(input.imageMediaIds ?? [])],
  };
}

function ToolbarButton({
  children,
  disabled = false,
  label,
  onClick,
}: {
  children: ReactNode;
  disabled?: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-label={label}
      className="grid size-10 place-items-center rounded-lg text-[var(--theme-text)] hover:bg-[var(--theme-surface)] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-40"
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function sameStringList(current: string[], saved: string[]): boolean {
  return (
    current.length === saved.length &&
    current.every((value, index) => value === saved[index])
  );
}

function reorderCommunityImages(
  imageIds: string[],
  index: number,
  direction: -1 | 1,
): string[] {
  const target = index + direction;
  if (target < 0 || target >= imageIds.length) return imageIds;
  const reordered = [...imageIds];
  [reordered[index], reordered[target]] = [reordered[target]!, reordered[index]!];
  return reordered;
}

function getErrorMessage(error: unknown): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof error.message === "string"
  ) {
    return error.message;
  }
  return "Không thể lưu bài viết. Vui lòng thử lại.";
}
