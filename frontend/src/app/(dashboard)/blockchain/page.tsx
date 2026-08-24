import { RoleGate } from "@/components/auth/role-gate";
import { BlockchainSigningWorkspace } from "@/components/blockchain/blockchain-signing-workspace";

export default function BlockchainSigningPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <BlockchainSigningWorkspace />
    </RoleGate>
  );
}
