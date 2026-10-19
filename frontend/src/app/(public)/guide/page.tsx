import type { Metadata } from "next";

import { GuideCenter } from "@/components/guide/guide-center";

export const metadata: Metadata = {
  title: "Trung tâm hướng dẫn",
  description:
    "Hướng dẫn từng bước sử dụng thư viện đề cử, tài khoản, hồ sơ và các dịch vụ công khai của Tinh Hoa Việt.",
  alternates: { canonical: "/guide" },
  openGraph: {
    title: "Trung tâm hướng dẫn | Tinh Hoa Việt",
    description: "Tìm câu trả lời theo từng bước trong trung tâm hướng dẫn.",
    url: "/guide",
    type: "website",
  },
};

export default function UserGuidePage() {
  return <GuideCenter scope="public" />;
}
