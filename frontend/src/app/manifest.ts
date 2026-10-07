import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Đề cử Tinh Hoa Việt",
    short_name: "Tinh Hoa Việt",
    description:
      "Nền tảng đề cử, xác lập và tra cứu bằng xác lập tài sản số Tinh Hoa Việt.",
    lang: "vi",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "any",
    background_color: "#fffaf3",
    theme_color: "#720000",
    categories: ["business", "education", "productivity"],
    icons: [
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
      {
        src: "/assets/brand/thv-certificate-seal.png",
        sizes: "1254x1254",
        type: "image/png",
        purpose: "any",
      },
    ],
    shortcuts: [
      {
        name: "Tìm đề cử",
        short_name: "Tìm đề cử",
        url: "/search",
      },
      {
        name: "Tra cứu bằng xác lập",
        short_name: "Tra cứu",
        url: "/verify",
      },
    ],
  };
}
