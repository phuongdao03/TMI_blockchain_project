import { describe, expect, it } from "vitest";

import {
  isPublicCoverImage,
  publicCoverLoader,
} from "@/lib/media/public-cover-loader";

describe("public cover loader", () => {
  const cover = "/api/v1/public/works/work/media/relation?cover=true";

  it("chooses a bounded responsive image width", () => {
    expect(publicCoverLoader({ src: cover, width: 390 })).toBe(
      `${cover}&coverWidth=640`,
    );
    expect(publicCoverLoader({ src: cover, width: 2400 })).toBe(
      `${cover}&coverWidth=1280`,
    );
  });

  it("applies only to editorial cover URLs", () => {
    expect(isPublicCoverImage(cover)).toBe(true);
    expect(
      isPublicCoverImage("https://res.cloudinary.com/demo/image/upload/a.webp"),
    ).toBe(false);
    expect(isPublicCoverImage(null)).toBe(false);
  });
});
