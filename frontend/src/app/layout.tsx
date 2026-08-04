import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppProviders } from "@/components/providers/app-providers";
import { canonicalSiteUrl } from "@/lib/seo";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: canonicalSiteUrl(),
  title: {
    default: "TMI Certificate",
    template: "%s | TMI Certificate",
  },
  description: "Nền tảng chứng thư tài sản số có thể xác minh.",
  icons: {
    icon: "/assets/brand/tmi-group-logo.png",
  },
  openGraph: {
    type: "website",
    locale: "vi_VN",
    siteName: "TMI Certificate",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html data-scroll-behavior="smooth" lang="vi">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
