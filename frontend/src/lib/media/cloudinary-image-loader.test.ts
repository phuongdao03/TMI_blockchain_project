import { describe, expect, it } from "vitest";

import {
  cloudinaryPublicImageLoader,
  isCloudinaryPublicImage,
} from "@/lib/media/cloudinary-image-loader";

describe("Cloudinary public image loader", () => {
  it("serves a smaller automatic-format image on mobile", () => {
    const src =
      "https://res.cloudinary.com/demo/image/upload/c_limit,w_1600,h_1600,q_auto,f_webp/v123/public/photo.webp";
    expect(cloudinaryPublicImageLoader({ src, width: 390 })).toBe(
      "https://res.cloudinary.com/demo/image/upload/c_limit,w_640,q_auto,f_auto/v123/public/photo.webp",
    );
  });

  it("accepts only Cloudinary delivery URLs", () => {
    expect(isCloudinaryPublicImage("/api/v1/public/works/a/media/b")).toBe(
      false,
    );
    expect(
      isCloudinaryPublicImage("https://example.com/image/upload/a.webp"),
    ).toBe(false);
    expect(
      isCloudinaryPublicImage(
        "https://res.cloudinary.com/demo/video/upload/so_auto,q_auto,f_webp/v123/public/video.webp",
      ),
    ).toBe(false);
  });
});
