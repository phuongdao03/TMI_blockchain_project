import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { AppProviders } from "@/components/providers/app-providers";
import { canonicalSiteUrl } from "@/lib/seo";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: canonicalSiteUrl(),
  title: {
    default: "Đề cử Tinh Hoa Việt",
    template: "%s | Đề cử Tinh Hoa Việt",
  },
  description:
    "Khám phá những đề cử tiêu biểu, câu chuyện giá trị Việt và thông tin minh bạch của chương trình.",
  icons: {
    icon: "/assets/brand/thv-brand-emblem.png",
    apple: "/apple-touch-icon.png",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Tinh Hoa Việt",
  },
  openGraph: {
    type: "website",
    locale: "vi_VN",
    siteName: "Đề cử Tinh Hoa Việt",
  },
};

export const viewport: Viewport = {
  colorScheme: "light dark",
  themeColor: "#720000",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html data-scroll-behavior="smooth" lang="vi" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(()=>{try{const p=localStorage.getItem('thv-theme')||'system';const t=p==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):p;document.documentElement.dataset.theme=t;document.documentElement.dataset.themePreference=p}catch{document.documentElement.dataset.theme='light'}})()",
          }}
        />
      </head>
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
