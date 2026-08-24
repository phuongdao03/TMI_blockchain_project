"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpenText,
  Eye,
  ImageIcon,
  LayoutTemplate,
  Send,
  Tags,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { PublicWorkEditor } from "@/components/admin/public-work-editor";
import { cmsApi } from "@/lib/api/client";

type CmsSection = "publicWorks" | "posts" | "pages" | "banners" | "categories";

const sections = [
  { id: "publicWorks", label: "Tác phẩm công khai", icon: Eye },
  { id: "posts", label: "Bài viết", icon: BookOpenText },
  { id: "pages", label: "Trang", icon: LayoutTemplate },
  { id: "banners", label: "Banner", icon: ImageIcon },
  { id: "categories", label: "Danh mục", icon: Tags },
] as const;

const inputClass =
  "min-h-11 w-full rounded-xl border border-neutral-200 bg-white px-3 text-sm outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-100";

export function CmsWorkspace() {
  const [section, setSection] = useState<CmsSection>("publicWorks");

  return (
    <div className="cms-workspace mx-auto max-w-7xl space-y-7">
      <header className="rounded-3xl bg-neutral-950 px-6 py-7 text-white sm:px-8">
        <p className="flex items-center gap-2 text-sm font-bold text-primary-300">
          <BookOpenText className="size-4" /> CMS nội bộ
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">
          Trung tâm nội dung
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-300">
          Quản lý nội dung công khai, xem trước bản đã làm sạch và kiểm soát
          thời điểm xuất bản.
        </p>
      </header>

      <nav
        aria-label="Nhóm nội dung"
        className="flex gap-2 overflow-x-auto rounded-2xl border border-neutral-200 bg-white p-2"
      >
        {sections.map((item) => {
          const Icon = item.icon;
          return (
            <button
              aria-current={section === item.id ? "page" : undefined}
              className={`inline-flex min-h-11 shrink-0 items-center gap-2 rounded-xl px-4 text-sm font-bold transition ${section === item.id ? "bg-neutral-950 text-white" : "text-neutral-600 hover:bg-neutral-100"}`}
              key={item.id}
              onClick={() => setSection(item.id)}
              type="button"
            >
              <Icon className="size-4" /> {item.label}
            </button>
          );
        })}
      </nav>

      {section === "publicWorks" ? <PublicWorkEditor /> : null}
      {section === "posts" ? <PostManager /> : null}
      {section === "pages" ? <PageManager /> : null}
      {section === "banners" ? <BannerManager /> : null}
      {section === "categories" ? <CategoryManager /> : null}
    </div>
  );
}

function PostManager() {
  const queryClient = useQueryClient();
  const [previewId, setPreviewId] = useState<string>();
  const [form, setForm] = useState({
    title: "",
    slug: "",
    excerpt: "",
    bodyHtml: "<p></p>",
  });
  const posts = useQuery({
    queryKey: ["cms", "posts"],
    queryFn: () => cmsApi.list(),
  });
  const create = useMutation({
    mutationFn: cmsApi.create,
    onSuccess: async () => {
      setForm({ title: "", slug: "", excerpt: "", bodyHtml: "<p></p>" });
      await queryClient.invalidateQueries({ queryKey: ["cms", "posts"] });
    },
  });
  const publish = useMutation({
    mutationFn: cmsApi.publish,
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["cms", "posts"] }),
  });
  const selected = posts.data?.data.find((item) => item.id === previewId);

  return (
    <div className="grid gap-6 xl:grid-cols-[24rem_minmax(0,1fr)]">
      <form
        className="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5"
        onSubmit={(event) => {
          event.preventDefault();
          create.mutate({ ...form, excerpt: form.excerpt || null });
        }}
      >
        <h2 className="text-lg font-bold">Bài viết mới</h2>
        <TextField
          label="Tiêu đề"
          onChange={(value) =>
            setForm((current) => ({ ...current, title: value }))
          }
          value={form.title}
        />
        <TextField
          label="Slug"
          onChange={(value) =>
            setForm((current) => ({ ...current, slug: value }))
          }
          value={form.slug}
        />
        <TextField
          label="Mô tả ngắn"
          onChange={(value) =>
            setForm((current) => ({ ...current, excerpt: value }))
          }
          required={false}
          value={form.excerpt}
        />
        <HtmlField
          onChange={(value) =>
            setForm((current) => ({ ...current, bodyHtml: value }))
          }
          value={form.bodyHtml}
        />
        <MutationFeedback error={create.error} />
        <Button className="w-full" disabled={create.isPending} type="submit">
          Lưu bản nháp
        </Button>
      </form>
      <ContentList loading={posts.isPending} title="Bài viết gần đây">
        {posts.data?.data.map((post) => (
          <ContentRow
            key={post.id}
            onPreview={() => setPreviewId(post.id)}
            onPublish={() => publish.mutate(post.id)}
            published={post.status === "PUBLISHED"}
            slug={post.slug}
            status={post.status}
            title={post.title}
            version={post.version}
          />
        ))}
      </ContentList>
      {selected ? (
        <Preview bodyHtml={selected.bodyHtml} title={selected.title} />
      ) : null}
    </div>
  );
}

function PageManager() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    title: "",
    slug: "",
    bodyHtml: "<p></p>",
  });
  const pages = useQuery({
    queryKey: ["cms", "pages"],
    queryFn: cmsApi.listPages,
  });
  const create = useMutation({
    mutationFn: cmsApi.createPage,
    onSuccess: async () => {
      setForm({ title: "", slug: "", bodyHtml: "<p></p>" });
      await queryClient.invalidateQueries({ queryKey: ["cms", "pages"] });
    },
  });
  const publish = useMutation({
    mutationFn: cmsApi.publishPage,
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["cms", "pages"] }),
  });
  return (
    <div className="grid gap-6 xl:grid-cols-[24rem_minmax(0,1fr)]">
      <form
        className="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5"
        onSubmit={(event) => {
          event.preventDefault();
          create.mutate(form);
        }}
      >
        <h2 className="text-lg font-bold">Trang mới</h2>
        <TextField
          label="Tiêu đề"
          value={form.title}
          onChange={(value) =>
            setForm((current) => ({ ...current, title: value }))
          }
        />
        <TextField
          label="Slug"
          value={form.slug}
          onChange={(value) =>
            setForm((current) => ({ ...current, slug: value }))
          }
        />
        <HtmlField
          value={form.bodyHtml}
          onChange={(value) =>
            setForm((current) => ({ ...current, bodyHtml: value }))
          }
        />
        <MutationFeedback error={create.error} />
        <Button className="w-full" disabled={create.isPending} type="submit">
          Lưu trang
        </Button>
      </form>
      <ContentList loading={pages.isPending} title="Trang nội dung">
        {pages.data?.map((page) => (
          <ContentRow
            key={page.id}
            onPublish={() => publish.mutate(page.id)}
            published={page.status === "PUBLISHED"}
            slug={page.slug}
            status={page.status}
            title={page.title}
            version={page.version}
          />
        ))}
      </ContentList>
    </div>
  );
}

function BannerManager() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    title: "",
    slug: "",
    imageUrl: "",
    linkUrl: "",
  });
  const banners = useQuery({
    queryKey: ["cms", "banners"],
    queryFn: cmsApi.listBanners,
  });
  const create = useMutation({
    mutationFn: cmsApi.createBanner,
    onSuccess: async () => {
      setForm({ title: "", slug: "", imageUrl: "", linkUrl: "" });
      await queryClient.invalidateQueries({ queryKey: ["cms", "banners"] });
    },
  });
  const publish = useMutation({
    mutationFn: cmsApi.publishBanner,
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["cms", "banners"] }),
  });
  return (
    <div className="grid gap-6 xl:grid-cols-[24rem_minmax(0,1fr)]">
      <form
        className="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5"
        onSubmit={(event) => {
          event.preventDefault();
          create.mutate({ ...form, linkUrl: form.linkUrl || null });
        }}
      >
        <h2 className="text-lg font-bold">Banner mới</h2>
        <TextField
          label="Tiêu đề"
          value={form.title}
          onChange={(value) =>
            setForm((current) => ({ ...current, title: value }))
          }
        />
        <TextField
          label="Slug"
          value={form.slug}
          onChange={(value) =>
            setForm((current) => ({ ...current, slug: value }))
          }
        />
        <TextField
          label="URL hình ảnh"
          value={form.imageUrl}
          onChange={(value) =>
            setForm((current) => ({ ...current, imageUrl: value }))
          }
        />
        <TextField
          label="URL liên kết"
          required={false}
          value={form.linkUrl}
          onChange={(value) =>
            setForm((current) => ({ ...current, linkUrl: value }))
          }
        />
        <MutationFeedback error={create.error} />
        <Button className="w-full" disabled={create.isPending} type="submit">
          Lưu banner
        </Button>
      </form>
      <ContentList loading={banners.isPending} title="Banner chiến dịch">
        {banners.data?.map((banner) => (
          <ContentRow
            key={banner.id}
            onPublish={() => publish.mutate(banner.id)}
            published={banner.status === "PUBLISHED"}
            slug={banner.slug}
            status={banner.status}
            title={banner.title}
            version={banner.version}
          />
        ))}
      </ContentList>
    </div>
  );
}

function CategoryManager() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", slug: "", description: "" });
  const categories = useQuery({
    queryKey: ["cms", "categories"],
    queryFn: cmsApi.listCategories,
  });
  const create = useMutation({
    mutationFn: cmsApi.createCategory,
    onSuccess: async () => {
      setForm({ name: "", slug: "", description: "" });
      await queryClient.invalidateQueries({ queryKey: ["cms", "categories"] });
    },
  });
  return (
    <div className="grid gap-6 xl:grid-cols-[24rem_minmax(0,1fr)]">
      <form
        className="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5"
        onSubmit={(event) => {
          event.preventDefault();
          create.mutate({ ...form, description: form.description || null });
        }}
      >
        <h2 className="text-lg font-bold">Danh mục mới</h2>
        <TextField
          label="Tên danh mục"
          value={form.name}
          onChange={(value) =>
            setForm((current) => ({ ...current, name: value }))
          }
        />
        <TextField
          label="Slug"
          value={form.slug}
          onChange={(value) =>
            setForm((current) => ({ ...current, slug: value }))
          }
        />
        <TextField
          label="Mô tả"
          required={false}
          value={form.description}
          onChange={(value) =>
            setForm((current) => ({ ...current, description: value }))
          }
        />
        <MutationFeedback error={create.error} />
        <Button className="w-full" disabled={create.isPending} type="submit">
          Lưu danh mục
        </Button>
      </form>
      <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div className="border-b border-neutral-200 px-5 py-4">
          <h2 className="font-bold">Danh mục hiện có</h2>
        </div>
        {categories.data?.map((category) => (
          <article
            className="border-b border-neutral-100 p-5 last:border-0"
            key={category.id}
          >
            <h3 className="font-bold">{category.name}</h3>
            <p className="mt-1 text-sm text-neutral-500">/{category.slug}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
  required = true,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-bold">{label}</span>
      <input
        className={inputClass}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        value={value}
      />
    </label>
  );
}

function HtmlField({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-bold">
        Nội dung HTML giới hạn
      </span>
      <textarea
        className={`${inputClass} min-h-44 py-3 font-mono`}
        onChange={(event) => onChange(event.target.value)}
        required
        value={value}
      />
    </label>
  );
}

function MutationFeedback({ error }: { error: Error | null }) {
  return error ? (
    <p className="text-sm font-semibold text-error" role="alert">
      Không thể lưu. Kiểm tra slug và dữ liệu nhập.
    </p>
  ) : null;
}

function ContentList({
  title,
  loading,
  children,
}: {
  title: string;
  loading: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      <div className="border-b border-neutral-200 px-5 py-4">
        <h2 className="font-bold">{title}</h2>
      </div>
      {loading ? (
        <p className="p-6 text-sm text-neutral-500" role="status">
          Đang tải nội dung...
        </p>
      ) : null}
      <div className="divide-y divide-neutral-100">{children}</div>
    </section>
  );
}

function ContentRow({
  title,
  slug,
  status,
  version,
  published,
  onPublish,
  onPreview,
}: {
  title: string;
  slug: string;
  status: string;
  version: number;
  published: boolean;
  onPublish: () => void;
  onPreview?: () => void;
}) {
  return (
    <article className="grid gap-4 p-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-bold">{title}</h3>
          <span className="rounded-md bg-neutral-100 px-2 py-1 text-xs font-bold">
            {status}
          </span>
        </div>
        <p className="mt-1 text-sm text-neutral-500">
          /{slug} · phiên bản {version}
        </p>
      </div>
      <div className="flex gap-2">
        {onPreview ? (
          <button
            className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-neutral-200 px-3 text-sm font-bold"
            onClick={onPreview}
            type="button"
          >
            <Eye className="size-4" />
            Xem trước
          </button>
        ) : null}
        {!published ? (
          <button
            className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-neutral-950 px-3 text-sm font-bold text-white"
            onClick={onPublish}
            type="button"
          >
            <Send className="size-4" />
            Xuất bản
          </button>
        ) : null}
      </div>
    </article>
  );
}

function Preview({ title, bodyHtml }: { title: string; bodyHtml: string }) {
  return (
    <section
      aria-label="Xem trước nội dung"
      className="rounded-2xl border border-neutral-200 bg-white p-6 xl:col-span-2"
    >
      <p className="text-xs font-bold uppercase tracking-wider text-neutral-500">
        Bản xem trước đã được làm sạch
      </p>
      <h2 className="mt-3 text-2xl font-bold">{title}</h2>
      <div
        className="prose mt-4 max-w-none text-neutral-700"
        dangerouslySetInnerHTML={{ __html: bodyHtml }}
      />
    </section>
  );
}
