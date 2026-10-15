import type { Metadata } from "next";

import { CommunityPostDetail } from "@/components/community/community-post-detail";
import { loadCommunityPost } from "@/lib/api/community-post-server";

const fallbackTitle = "Bài viết cộng đồng";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await loadCommunityPost(slug);
  if (!post) {
    return { title: fallbackTitle, robots: { index: false, follow: false } };
  }

  const description = post.excerpt?.trim() || post.content.trim().slice(0, 160);
  const canonical = `/community/posts/${encodeURIComponent(post.slug)}`;
  return {
    title: post.title,
    description,
    alternates: { canonical },
    openGraph: {
      title: post.title,
      description,
      type: "article",
      url: canonical,
      publishedTime: post.publishedAt,
    },
  };
}

export default async function CommunityPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <CommunityPostDetail slug={slug} />;
}
