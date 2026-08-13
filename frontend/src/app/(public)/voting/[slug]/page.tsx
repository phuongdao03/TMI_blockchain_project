import { CampaignDetail } from "@/components/voting/campaign-detail";

export default async function VotingCampaignPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <CampaignDetail slug={slug} />;
}
