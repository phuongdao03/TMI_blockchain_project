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
        src: "/assets/brand/logo-tinh-hoa-viet.png",
        sizes: "2048x2048",
        type: "image/png",
        purpose: "any",
      },
    ]);
  });
});
