import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { PublicWorkCard } from "@/components/public/public-work-card";
import type { PublicCatalogWork } from "@/lib/api/types";

const work: PublicCatalogWork = {
  id: "work-1",
  slug: "tac-pham",
  title: "Tác phẩm",
  shortDescription: "Giới thiệu",
  authorDisplayName: "Tác giả",
  categoryName: "Nghệ thuật",
  categorySlug: "nghe-thuat",
  tags: [],
  publishedAt: "2026-10-01T00:00:00Z",
  isFeatured: false,
  thumbnailUrl: "/api/v1/public/works/work-1/media/cover-1?cover=true",
  thumbnailAltText: "Ảnh bìa tác phẩm",
};

it("renders responsive cover URLs for the public catalog", () => {
  render(<PublicWorkCard work={work} position={1} source="list" />);

  const image = screen.getByRole("img", { name: "Ảnh bìa tác phẩm" });
  expect(image.getAttribute("srcset")).toContain("coverWidth=640");
  expect(image.getAttribute("src")).toContain("coverWidth=1280");
});
