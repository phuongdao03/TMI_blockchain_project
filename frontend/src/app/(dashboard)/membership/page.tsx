import type { CommunityChatRoom } from "@/components/membership/community-chat";
import { MembershipWorkspace } from "@/components/membership/membership-workspace";

export default async function MembershipPage({
  searchParams,
}: {
  searchParams: Promise<{ room?: string | string[] }>;
}) {
  const params = await searchParams;
  const requestedRoom = Array.isArray(params.room)
    ? params.room[0]
    : params.room;
  const initialChatRoom: CommunityChatRoom =
    requestedRoom === "COMPANION" || requestedRoom === "PRESTIGE"
      ? requestedRoom
      : "MEMBER";

  return <MembershipWorkspace initialChatRoom={initialChatRoom} />;
}
