import type { Metadata } from "next";

import { GuideArticleReader } from "@/components/guide/guide-article-reader";

export const metadata: Metadata = {
  title: "Hướng dẫn trong tài khoản",
  robots: { index: false, follow: false },
};

export default async function AccountGuideArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <GuideArticleReader scope="account" slug={slug} />;
}
