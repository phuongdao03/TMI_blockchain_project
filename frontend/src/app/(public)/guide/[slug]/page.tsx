import type { Metadata } from "next";

import { GuideArticleReader } from "@/components/guide/guide-article-reader";
import { loadPublicGuideArticle } from "@/lib/api/guide-seo-server";

const fallbackTitle = "Hướng dẫn sử dụng";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const article = await loadPublicGuideArticle(slug);
  if (!article) {
    return { title: fallbackTitle, robots: { index: false, follow: false } };
  }
  const canonical = `/guide/${encodeURIComponent(article.slug)}`;
  return {
    title: article.title,
    description: article.summary,
    alternates: { canonical },
    openGraph: {
      title: article.title,
      description: article.summary,
      type: "article",
      url: canonical,
      modifiedTime: article.updatedAt,
    },
  };
}

export default async function PublicGuideArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <GuideArticleReader scope="public" slug={slug} />;
}
