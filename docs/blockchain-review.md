# Blockchain Review — THV / Tinh Hoa Việt

## Classification

| Area | Status | Evidence |
| --- | --- | --- |
| Certificate anchoring and confirmation workflow | IMPLEMENTED | Blockchain service, gateway, signer, workers, migrations, and focused tests exist. |
| Certificate version/revocation anchoring | IMPLEMENTED | Version lifecycle service and focused blockchain tests exist. |
| Public verification contract | IMPLEMENTED | Public verification API and focused contract tests exist. |
| User-facing THV verification language | PARTIAL | Existing UI still uses the legacy visual system and has not passed its shell tests. |
| Production chain/RPC/signer readiness | NOT VERIFIED | Requires approved environment, provider, and release evidence. |

## Findings

- Blockchain is correctly modelled as a backend proof workflow, not a browser
  wallet flow.
- The source contains durable broadcast, confirmation, and reconciliation work;
  this should remain the integration boundary.
- No claim should be made that a production anchor is confirmed without the
  persisted transaction status and receipt evidence.
- Do not change chain, signer, or RPC configuration without explicit approval.

## Release gate

Before a production claim: run the document-proof gate, verify the selected
network and the active Super Admin human-signing wallet, inspect a successful
confirmation and failure/retry path, and validate public verification without
revealing private documents or operational identifiers.
