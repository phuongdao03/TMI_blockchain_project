import { beforeEach, describe, expect, it, vi } from "vitest";

const server = vi.hoisted(() => ({ loadCommunityPost: vi.fn() }));
vi.mock("@/lib/api/community-post-server", () => server);
vi.mock("@/components/community/community-post-detail", () => ({
  CommunityPostDetail: (props: Record<string, unknown>) => <div data-slug={props.slug} />,
}));

import CommunityPostPage, { generateMetadata } from "@/app/(public)/community/posts/[slug]/page";

const post = {
  id: "post-1", slug: "lang-nghe-va-ky-uc", title: "Làng nghề và ký ức", excerpt: "Câu chuyện về nghề truyền thống.",
  category: { id: "cat-1", name: "Di sản", slug: "di-san" },
  author: { id: "member-1", username: "minh", displayName: "Minh", avatarUrl: null },
  publishedAt: "2026-10-12T09:00:00Z", likeCount: 2, commentCount: 1, viewerHasLiked: false, viewerHasBookmarked: false,
  tags: [], relatedWork: null, images: [], content: "Nội dung đầy đủ.",
};

describe("CommunityPostPage metadata", () => {
  beforeEach(() => vi.clearAllMocks());

  it("exposes the public post title, excerpt, canonical path, and Open Graph metadata", async () => {
    server.loadCommunityPost.mockResolvedValue(post);
    const metadata = await generateMetadata({ params: Promise.resolve({ slug: post.slug }) });

    expect(metadata.title).toBe(post.title);
    expect(metadata.description).toBe(post.excerpt);
    expect(metadata.alternates?.canonical).toBe(`/community/posts/${post.slug}`);
    expect(metadata.openGraph).toMatchObject({ title: post.title, description: post.excerpt, type: "article" });
    expect(metadata.robots).toBeUndefined();
  });

  it("uses a generic noindex fallback when public post data cannot load", async () => {
    server.loadCommunityPost.mockResolvedValue(null);
    const metadata = await generateMetadata({ params: Promise.resolve({ slug: "missing" }) });

    expect(metadata.title).toBe("Bài viết cộng đồng");
    expect(metadata.robots).toEqual({ index: false, follow: false });
    expect(metadata.openGraph).toBeUndefined();
  });

  it("renders the requested public slug", async () => {
    const page = await CommunityPostPage({ params: Promise.resolve({ slug: post.slug }) });
    expect(page.props.slug).toBe(post.slug);
  });
});
