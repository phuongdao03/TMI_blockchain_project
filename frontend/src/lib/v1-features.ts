import { releaseMode, type ReleaseMode } from "@/lib/release-mode";

export type FeatureAvailability = "enabled" | "coming-soon" | "hidden";
export type PublicFeatureKey =
  | "publicCatalog"
  | "authentication"
  | "verification"
  | "voting"
  | "submission"
  | "payment";

interface PublicFeatureDefinition {
  label: string;
  href: string;
  preview: FeatureAvailability;
  full: FeatureAvailability;
}

export const publicV1Features = {
  publicCatalog: {
    label: "Đề cử",
    href: "/works",
    preview: "enabled",
    full: "enabled",
  },
  authentication: {
    label: "Tài khoản",
    href: "/login",
    preview: "enabled",
    full: "enabled",
  },
  verification: {
    label: "Minh bạch",
    href: "/verify",
    preview: "enabled",
    full: "enabled",
  },
  voting: {
    label: "Bình chọn",
    href: "/coming-soon/voting",
    preview: "coming-soon",
    full: "enabled",
  },
  submission: {
    label: "Gửi đề cử",
    href: "/coming-soon/submission",
    preview: "coming-soon",
    full: "enabled",
  },
  payment: {
    label: "Thanh toán",
    href: "/payments",
    preview: "hidden",
    full: "enabled",
  },
} as const satisfies Record<PublicFeatureKey, PublicFeatureDefinition>;

export function featureAvailability(
  feature: PublicFeatureKey,
  mode: ReleaseMode = releaseMode(),
): FeatureAvailability {
  return publicV1Features[feature][mode];
}
