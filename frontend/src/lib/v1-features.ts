export type ReleaseMode = "preview" | "full";

export type PublicFeatureKey =
  | "catalog"
  | "authentication"
  | "verification"
  | "voting"
  | "submission"
  | "payment";

export type PublicFeatureStatus = "enabled" | "coming-soon" | "hidden";

export type PublicFeature = {
  key: PublicFeatureKey;
  label: string;
  href: string;
  preview: PublicFeatureStatus;
  full: PublicFeatureStatus;
};

const features: PublicFeature[] = [
  {
    key: "catalog",
    label: "Đề cử",
    href: "/works",
    preview: "enabled",
    full: "enabled",
  },
  {
    key: "authentication",
    label: "Đăng nhập",
    href: "/login",
    preview: "enabled",
    full: "enabled",
  },
  {
    key: "verification",
    label: "Minh bạch",
    href: "/verify",
    preview: "enabled",
    full: "enabled",
  },
  {
    key: "voting",
    label: "Bình chọn",
    href: "/coming-soon/voting",
    preview: "coming-soon",
    full: "enabled",
  },
  {
    key: "submission",
    label: "Gửi đề cử",
    href: "/coming-soon/submission",
    preview: "coming-soon",
    full: "enabled",
  },
  {
    key: "payment",
    label: "Thanh toán",
    href: "/payments",
    preview: "hidden",
    full: "enabled",
  },
];

export function getReleaseMode(): ReleaseMode {
  return process.env.NEXT_PUBLIC_RELEASE_MODE === "preview"
    ? "preview"
    : "full";
}

export function getPublicFeatureStatus(
  key: PublicFeatureKey,
  mode = getReleaseMode(),
): PublicFeatureStatus {
  const feature = features.find((item) => item.key === key);
  return feature?.[mode] ?? "hidden";
}

export function getPublicFeatures(mode = getReleaseMode()) {
  return features
    .map((feature) => ({ ...feature, status: feature[mode] }))
    .filter((feature) => feature.status !== "hidden");
}

export const publicV1Features = Object.fromEntries(
  features.map((feature) => [feature.key, feature]),
) as Record<PublicFeatureKey, PublicFeature>;

export function featureAvailability(
  key: PublicFeatureKey | "publicCatalog",
  mode = getReleaseMode(),
): PublicFeatureStatus {
  return getPublicFeatureStatus(
    key === "publicCatalog" ? "catalog" : key,
    mode,
  );
}
