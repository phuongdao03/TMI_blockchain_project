# Signer rotation and incident response

Rotation has two distinct controls:

1. Governance wallet revokes `ISSUER_ROLE` from the old address and grants it to the new public address on the intended network.
2. The old designated THV signer uses **Ký blockchain** to revoke the active wallet link. THV cancels outstanding unsigned intents and restores affected transactions to the signer queue. The new designated THV account then completes the ownership challenge.

For suspected compromise, revoke the on-chain role first. Do not wait for the off-chain UI. Record the incident ID, old/new public addresses, operator, approvals, on-chain transaction hashes and time in the security/audit process.

Never rotate by editing a database wallet address. The new holder must prove ownership by signing a fresh one-time challenge. Existing confirmed proofs remain historical facts and are not deleted; a corrected dossier proceeds as a new version and proof.
