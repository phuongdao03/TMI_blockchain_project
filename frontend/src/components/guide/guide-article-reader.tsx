"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Clock3, ListTree } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { guideApi } from "@/lib/api/client";
import { guideCategoryLabel } from "@/components/guide/guide-center";
import { prepareGuideArticleBody } from "@/components/guide/guide-content";
import { useAuthUser } from "@/lib/auth/user-context";

export function GuideArticleReader({
  scope,
  slug,
}: {
  scope: "public" | "account";
  slug: string;
}) {
  const user = useAuthUser();
  const accessKey =
    scope === "account"
      ? `${user?.id ?? "signed-out"}:${user?.roles?.join(",") ?? ""}:${user?.isEmployee ? "employee" : "standard"}`
      : "public";
  const [activeHeading, setActiveHeading] = useState<string | null>(null);
  const articleQuery = useQuery({
    queryKey: ["guide-article", scope, accessKey, slug],
    queryFn: () =>
      scope === "public"
        ? guideApi.publicArticle(slug)
        : guideApi.accessibleArticle(slug),
  });
  const listQuery = useQuery({
    queryKey: ["guide-article-navigation", scope, accessKey],
    queryFn: () =>
      scope === "public"
        ? guideApi.publicList({ page: 1, pageSize: 100 })
        : guideApi.accessibleList({ page: 1, pageSize: 100 }),
  });
  const loadedArticle = articleQuery.data;
  const content = useMemo(
    () => prepareGuideArticleBody(loadedArticle?.bodyHtml ?? ""),
    [loadedArticle?.bodyHtml],
  );
  useEffect(() => {
    if (!content.headings.length || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const current = entries
          .filter((entry) => entry.isIntersecting)
          .sort(
            (left, right) =>
              left.boundingClientRect.top - right.boundingClientRect.top,
          )[0];
        const headingId = current?.target.getAttribute("id");
        if (headingId) setActiveHeading(headingId);
      },
      { rootMargin: "-96px 0px -68% 0px", threshold: 0 },
    );
    for (const heading of content.headings) {
      const element = document.getElementById(heading.id);
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
  }, [content.headings]);

  if (articleQuery.isPending) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-12" aria-live="polite">
        <p className="rounded-xl border border-[var(--theme-border)] p-6 text-sm text-[var(--theme-muted)]">
          Đang mở bài hướng dẫn…
        </p>
      </div>
    );
  }
  if (articleQuery.isError || !loadedArticle) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <div className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-7">
          <h1 className="text-2xl font-bold text-[var(--theme-text)]">
            Không tìm thấy hướng dẫn
          </h1>
          <p className="mt-3 text-sm leading-6 text-[var(--theme-muted)]">
            Bài viết có thể đã được chuyển hoặc tài khoản hiện tại chưa có quyền
            xem.
          </p>
          <Link
            className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-white"
            href={scope === "public" ? "/guide" : "/help"}
          >
            <ArrowLeft aria-hidden="true" className="size-4" />
            Về danh sách hướng dẫn
          </Link>
        </div>
      </div>
    );
  }

  const article = loadedArticle;
  const visibleArticles = listQuery.data?.data ?? [];
  const categoryArticles = visibleArticles.filter(
    (item) => item.category === article.category,
  );
  const currentIndex = categoryArticles.findIndex((item) => item.slug === slug);
  const previous = currentIndex > 0 ? categoryArticles[currentIndex - 1] : null;
  const next =
    currentIndex >= 0 && currentIndex < categoryArticles.length - 1
      ? categoryArticles[currentIndex + 1]
      : null;
  const basePath = scope === "public" ? "/guide" : "/help";

  return (
    <div className="guide-reader mx-auto w-full max-w-5xl px-4 py-5 text-[var(--theme-text)] sm:px-6 sm:py-9 lg:px-8">
      <ReturnToGuideList href={basePath} />
      <nav
        aria-label="Đường dẫn"
        className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[var(--theme-muted)] sm:text-sm"
      >
        <Link
          className="hover:text-[var(--theme-accent)] hover:underline focus:outline-none focus:ring-2 focus:ring-[var(--theme-accent)]"
          href={basePath}
        >
          Tất cả hướng dẫn
        </Link>
        <span aria-hidden="true">/</span>
        <Link
          className="hover:text-[var(--theme-accent)] hover:underline focus:outline-none focus:ring-2 focus:ring-[var(--theme-accent)]"
          href={`${basePath}?topic=${encodeURIComponent(article.category)}#all-guides`}
        >
          {guideCategoryLabel(article.category)}
        </Link>
      </nav>

      <article className="mt-4 max-w-3xl sm:mt-6">
        <header className="border-b border-[var(--theme-border)] pb-5 sm:pb-6">
          <p className="text-xs font-semibold text-[var(--theme-accent)] sm:text-sm">
            {guideCategoryLabel(article.category)}
          </p>
          <h1 className="mt-2 text-xl font-semibold leading-tight tracking-tight sm:text-4xl">
            {article.title}
          </h1>
          <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)] sm:mt-3 sm:text-base sm:leading-7">
            {article.summary}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-[0.7rem] text-[var(--theme-muted)] sm:mt-4 sm:text-xs">
            <span className="inline-flex items-center gap-1.5">
              <Clock3 aria-hidden="true" className="size-4" />
              {article.readingMinutes} phút đọc
            </span>
            <span>Cập nhật {formatDate(article.updatedAt)}</span>
          </div>
        </header>

        {content.headings.length > 1 && (
          <details className="mt-4 rounded-lg border border-[var(--theme-border)] px-3 py-2 sm:mt-6 sm:px-4 sm:py-3">
            <summary className="flex min-h-8 cursor-pointer items-center gap-2 text-sm font-semibold sm:text-base">
              <ListTree
                aria-hidden="true"
                className="size-4 text-[var(--theme-accent)]"
              />
              Trong bài này ({content.headings.length})
            </summary>
            <HeadingList activeId={activeHeading} headings={content.headings} />
          </details>
        )}

        <div
          className="guide-article-body mt-5 break-words text-[0.9rem] leading-[1.65] text-[var(--theme-text)] sm:mt-7 sm:text-base sm:leading-7 [&_a]:font-semibold [&_a]:text-[var(--theme-accent)] [&_a]:underline [&_blockquote]:my-5 [&_blockquote]:border-l-4 [&_blockquote]:border-[var(--theme-accent)] [&_blockquote]:bg-[var(--theme-elevated)] [&_blockquote]:px-4 [&_blockquote]:py-3 [&_h2]:mb-2 [&_h2]:mt-7 [&_h2]:scroll-mt-24 [&_h2]:text-lg [&_h2]:font-semibold [&_h3]:mb-2 [&_h3]:mt-6 [&_h3]:scroll-mt-24 [&_h3]:text-base [&_h3]:font-semibold [&_li]:ml-4 [&_ol]:my-3 [&_ol]:list-decimal [&_p]:my-3 [&_ul]:my-3 [&_ul]:list-disc sm:[&_h2]:mt-9 sm:[&_h2]:text-xl sm:[&_h3]:mt-7 sm:[&_h3]:text-lg sm:[&_li]:ml-5 sm:[&_ol]:my-4 sm:[&_p]:my-4 sm:[&_ul]:my-4"
          dangerouslySetInnerHTML={{ __html: content.html }}
        />

        {article.audiences.includes("PUBLIC") && (
          <GuideFeedback slug={article.slug} />
        )}

        {(previous || next) && (
          <nav
            aria-label="Chuyển bài"
            className="mt-9 flex flex-col gap-3 border-t border-[var(--theme-border)] pt-5 sm:flex-row sm:items-start sm:justify-between"
          >
            {previous ? (
              <Link
                className="max-w-full text-sm hover:text-[var(--theme-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--theme-accent)] sm:max-w-[48%]"
                href={`${basePath}/${previous.slug}`}
              >
                <span className="block text-xs text-[var(--theme-muted)]">
                  ← Bài trước
                </span>
                <span className="mt-1 block font-semibold">
                  {previous.title}
                </span>
              </Link>
            ) : (
              <span />
            )}
            {next && (
              <Link
                className="max-w-full text-left text-sm hover:text-[var(--theme-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--theme-accent)] sm:max-w-[48%] sm:text-right"
                href={`${basePath}/${next.slug}`}
              >
                <span className="block text-xs text-[var(--theme-muted)]">
                  Bài tiếp theo →
                </span>
                <span className="mt-1 block font-semibold">{next.title}</span>
              </Link>
            )}
          </nav>
        )}
        <div className="mt-8 border-t border-[var(--theme-border)] pt-5">
          <ReturnToGuideList href={basePath} />
        </div>
      </article>
    </div>
  );
}

function ReturnToGuideList({ href }: { href: string }) {
  return (
    <Link
      className="mb-5 inline-flex min-h-11 items-center gap-2 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm font-semibold text-[var(--theme-text)] transition-colors hover:border-[var(--theme-accent)] hover:text-[var(--theme-accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)]"
      href={href}
    >
      <ArrowLeft aria-hidden="true" className="size-4" />
      Quay lại danh sách hướng dẫn
    </Link>
  );
}

function HeadingList({
  headings,
  activeId,
}: {
  headings: Array<{ id: string; text: string; level: number }>;
  activeId: string | null;
}) {
  if (!headings.length) {
    return (
      <p className="mt-3 text-xs leading-5 text-[var(--theme-muted)]">
        Bài viết chưa có mục lục.
      </p>
    );
  }
  return (
    <nav aria-label="Mục lục" className="mt-3">
      <ul className="space-y-2">
        {headings.map((heading) => (
          <li className={heading.level === 3 ? "pl-3" : ""} key={heading.id}>
            <a
              aria-current={heading.id === activeId ? "location" : undefined}
              className={`block rounded-sm text-xs leading-5 hover:text-[var(--theme-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--theme-accent)] ${heading.id === activeId ? "font-semibold text-[var(--theme-accent)]" : "text-[var(--theme-muted)]"}`}
              href={`#${heading.id}`}
            >
              {heading.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function GuideFeedback({ slug }: { slug: string }) {
  const [helpful, setHelpful] = useState<boolean | null>(null);
  const [comment, setComment] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState("");
  const feedback = useMutation({
    mutationFn: async () => {
      const clientToken = getFeedbackToken();
      return guideApi.submitFeedback(slug, {
        helpful: helpful ?? false,
        comment: comment.trim() || null,
        clientToken,
      });
    },
    onSuccess: () => {
      try {
        window.localStorage.setItem(`guide-feedback:${slug}`, "sent");
      } catch {
        // The server still accepts this feedback if local storage is disabled.
      }
      setAccepted(true);
      setError("");
    },
    onError: () => setError("Không gửi được phản hồi. Vui lòng thử lại sau."),
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      if (window.localStorage.getItem(`guide-feedback:${slug}`) !== "sent")
        return;
      const timer = window.setTimeout(() => setAccepted(true), 0);
      return () => window.clearTimeout(timer);
    } catch {
      return;
    }
  }, [slug]);

  return (
    <section
      aria-labelledby="guide-feedback-heading"
      className="mt-10 border-t border-[var(--theme-border)] py-6 sm:rounded-2xl sm:border sm:bg-[var(--theme-elevated)] sm:p-6"
    >
      <h2 className="text-lg font-bold" id="guide-feedback-heading">
        Hướng dẫn này có hữu ích không?
      </h2>
      {accepted ? (
        <p
          aria-live="polite"
          className="mt-3 text-sm text-[var(--theme-muted)]"
        >
          Cảm ơn bạn đã gửi phản hồi.
        </p>
      ) : (
        <>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              aria-pressed={helpful === true}
              className={`min-h-10 rounded-lg border px-4 text-sm font-semibold ${helpful === true ? "border-[var(--theme-accent)] bg-[var(--theme-accent)] text-white" : "border-[var(--theme-border)]"}`}
              onClick={() => setHelpful(true)}
              type="button"
            >
              Có, hữu ích
            </button>
            <button
              aria-pressed={helpful === false}
              className={`min-h-10 rounded-lg border px-4 text-sm font-semibold ${helpful === false ? "border-[var(--theme-accent)] bg-[var(--theme-accent)] text-white" : "border-[var(--theme-border)]"}`}
              onClick={() => setHelpful(false)}
              type="button"
            >
              Chưa hữu ích
            </button>
          </div>
          <label className="mt-4 block text-sm font-semibold">
            Góp ý thêm{" "}
            <span className="font-normal text-[var(--theme-muted)]">
              (không bắt buộc)
            </span>
            <textarea
              className="mt-2 min-h-24 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 text-sm outline-none focus:border-[var(--theme-accent)]"
              maxLength={500}
              onChange={(event) => setComment(event.target.value)}
              placeholder="Cho chúng tôi biết phần nào cần làm rõ…"
              value={comment}
            />
          </label>
          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-[var(--theme-muted)]">
              Quản trị viên có quyền quản lý nội dung xem góp ý theo từng bài
              trong mục Quản lý bài viết hướng dẫn. Phản hồi không gắn với tên
              tài khoản.
            </p>
            <button
              className="min-h-11 rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-white disabled:opacity-50"
              disabled={helpful === null || feedback.isPending}
              onClick={() => feedback.mutate()}
              type="button"
            >
              {feedback.isPending ? "Đang gửi…" : "Gửi phản hồi"}
            </button>
          </div>
          {error && (
            <p className="mt-2 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}
        </>
      )}
    </section>
  );
}

function getFeedbackToken(): string {
  const key = "guide-feedback-token";
  try {
    const stored = window.localStorage.getItem(key);
    if (stored) return stored;
  } catch {
    // Use an in-memory random token when storage is unavailable.
  }
  const token = createAnonymousToken();
  try {
    window.localStorage.setItem(key, token);
  } catch {
    // Storage is optional; token remains anonymous and scoped to this request.
  }
  return token;
}

function createAnonymousToken(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = ((bytes[6] ?? 0) & 0x0f) | 0x40;
  bytes[8] = ((bytes[8] ?? 0) & 0x3f) | 0x80;
  const value = Array.from(bytes, (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
  return `${value.slice(0, 8)}-${value.slice(8, 12)}-${value.slice(12, 16)}-${value.slice(16, 20)}-${value.slice(20)}`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? "gần đây"
    : new Intl.DateTimeFormat("vi-VN", {
        day: "numeric",
        month: "long",
        year: "numeric",
      }).format(date);
}
