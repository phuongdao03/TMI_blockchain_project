import { describe, expect, it } from "vitest";

import manifest from "@/app/manifest";

describe("PWA manifest", () => {
  it("describes an installable Vietnamese standalone application", () => {
    const value = manifest();

    expect(value).toMatchObject({
      id: "/",
      lang: "vi",
      name: "Đề cử Tinh Hoa Việt",
      short_name: "Tinh Hoa Việt",
      start_url: "/",
      scope: "/",
      display: "standalone",
    });
    expect(value.icons).toEqual([
      {
        src: "/pwa-icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/pwa-icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
    ]);
  });
});
