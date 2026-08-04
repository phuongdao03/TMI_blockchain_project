import { VotingParticipantWorkspace } from "@/components/admin/voting-participant-workspace";
import { RoleGate } from "@/components/auth/role-gate";

export default function VotingParticipantsPage() {
  return (
    <RoleGate allowed={["CONTENT_ADMIN", "SUPER_ADMIN"]}>
      <VotingParticipantWorkspace />
    </RoleGate>
  );
}
