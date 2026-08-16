import { notFound } from "next/navigation";

import {
  ComingSoonFeature,
  type ComingSoonFeatureName,
} from "@/components/public/coming-soon-feature";

const supportedFeatures = new Set<ComingSoonFeatureName>([
  "voting",
  "submission",
]);

export function generateStaticParams() {
  return [...supportedFeatures].map((feature) => ({ feature }));
}

export default async function ComingSoonPage({
  params,
}: {
  params: Promise<{ feature: string }>;
}) {
  const { feature } = await params;
  if (!supportedFeatures.has(feature as ComingSoonFeatureName)) notFound();
  return <ComingSoonFeature feature={feature as ComingSoonFeatureName} />;
}
