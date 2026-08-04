import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";

import { PublicWorkDetailPage } from "@/components/public/public-work-detail";
import { loadPublicWork } from "@/lib/api/public-work-server";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const result = await loadPublicWork(slug);
  if (result.kind !== "detail") {
    return {
      title: "Tác phẩm công khai | TMI Certificate",
      robots: { index: false, follow: false },
    };
  }
  const work = result.detail;
  const thumbnail = work.media.find((item) => item.isThumbnail && item.url);
  return {
    title: `${work.title} | TMI Certificate`,
    description: work.shortDescription,
    alternates: { canonical: `/tai-san/${work.canonicalSlug}` },
    robots:
      work.visibility === "UNLISTED"
        ? { index: false, follow: false }
        : { index: true, follow: true },
    openGraph: {
      title: work.title,
      description: work.shortDescription,
      type: "article",
      publishedTime: work.publishedAt,
      images: thumbnail?.url
        ? [{ url: thumbnail.url, alt: thumbnail.altText || work.title }]
        : undefined,
    },
  };
}

export default async function PublicAssetPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const result = await loadPublicWork(slug);
  if (result.kind === "redirect") {
    permanentRedirect(`/tai-san/${encodeURIComponent(result.slug)}`);
  }
  if (result.kind === "not_found") notFound();
  return (
    <PublicWorkDetailPage
      initialDetail={result.kind === "detail" ? result.detail : undefined}
      slug={slug}
    />
  );
}
