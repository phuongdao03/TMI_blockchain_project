import type { PublicCatalogWork, PublicWorkDetail } from "@/lib/api/types";

export const previewWorks: PublicCatalogWork[] = [
  {
    id: "preview-lacquer-memory",
    slug: "ky-uc-son-mai",
    title: "Ký ức sơn mài",
    shortDescription:
      "Nội dung giới thiệu về một nghiên cứu chất liệu, ánh sáng và ký ức đô thị.",
    authorDisplayName: "Ban biên tập Tinh Hoa Việt",
    categoryName: "Mỹ thuật thị giác",
    categorySlug: "my-thuat-thi-giac",
    tags: [
      { name: "Sơn mài", slug: "son-mai" },
      { name: "Đương đại", slug: "duong-dai" },
    ],
    publishedAt: "2026-08-01T00:00:00Z",
    isFeatured: true,
    thumbnailUrl: null,
    thumbnailAltText: null,
  },
  {
    id: "preview-river-archive",
    slug: "luu-tru-cua-song",
    title: "Lưu trữ của sông",
    shortDescription:
      "Nội dung giới thiệu khám phá nhịp điệu, địa hình và những lớp ký ức ven sông.",
    authorDisplayName: "Ban biên tập Tinh Hoa Việt",
    categoryName: "Nhiếp ảnh",
    categorySlug: "nhiep-anh",
    tags: [
      { name: "Phong cảnh", slug: "phong-canh" },
      { name: "Tư liệu", slug: "tu-lieu" },
    ],
    publishedAt: "2026-08-03T00:00:00Z",
    isFeatured: true,
    thumbnailUrl: null,
    thumbnailAltText: null,
  },
  {
    id: "preview-digital-garden",
    slug: "khu-vuon-so",
    title: "Khu vườn số",
    shortDescription:
      "Nội dung giới thiệu về hình thái tự nhiên được tái diễn giải trong không gian số.",
    authorDisplayName: "Ban biên tập Tinh Hoa Việt",
    categoryName: "Nghệ thuật số",
    categorySlug: "nghe-thuat-so",
    tags: [
      { name: "Kỹ thuật số", slug: "ky-thuat-so" },
      { name: "Thử nghiệm", slug: "thu-nghiem" },
    ],
    publishedAt: "2026-08-05T00:00:00Z",
    isFeatured: true,
    thumbnailUrl: null,
    thumbnailAltText: null,
  },
];

export function resolvePreviewWork(slug: string): PublicWorkDetail | undefined {
  const work = previewWorks.find((item) => item.slug === slug);
  if (!work) return undefined;
  return {
    ...work,
    fullDescription:
      "Nội dung được giới thiệu nhằm giúp cộng đồng khám phá câu chuyện, giá trị và bối cảnh của tác phẩm. Thông tin xác nhận sẽ được bổ sung khi quá trình công bố hoàn tất.",
    organizationDisplayName: "TMI Group",
    visibility: "PUBLIC",
    certificate: null,
    proof: null,
    media: [],
    relatedWorks: previewWorks
      .filter((item) => item.id !== work.id)
      .slice(0, 2),
    canonicalSlug: work.slug,
    redirected: false,
  };
}

export function filterPreviewWorks({
  category,
  query,
  tag,
}: {
  category?: string;
  query?: string;
  tag?: string;
}): PublicCatalogWork[] {
  const normalizedQuery = query?.trim().toLocaleLowerCase("vi-VN");
  return previewWorks.filter((work) => {
    if (category && work.categorySlug !== category) return false;
    if (tag && !work.tags.some((item) => item.slug === tag)) return false;
    if (!normalizedQuery) return true;
    return [work.title, work.shortDescription, work.authorDisplayName]
      .filter(Boolean)
      .some((value) =>
        value!.toLocaleLowerCase("vi-VN").includes(normalizedQuery),
      );
  });
}
