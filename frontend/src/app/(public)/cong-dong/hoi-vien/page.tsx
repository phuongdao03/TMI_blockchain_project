import type { Metadata } from "next";

import { MembershipPricingPage } from "@/components/membership/membership-pricing-page";

export const metadata: Metadata = {
  title: "Hội viên Tinh Hoa Việt",
  description:
    "Kết nối giá trị, đồng hành phát triển và lan tỏa tinh hoa cùng cộng đồng hội viên Tinh Hoa Việt.",
  alternates: { canonical: "/cong-dong/hoi-vien" },
};

export default function PublicMembershipPricingRoute() {
  return <MembershipPricingPage />;
}
