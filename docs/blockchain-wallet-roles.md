# Wallet roles

THV has two wallet roles in production.

| Wallet | Owner | Purpose | Must not do |
|---|---|---|---|
| Governance/admin wallet | Controlled multisig or hardware-wallet process | Deploy, grant/revoke `ISSUER_ROLE`, pause/unpause and contract administration | Daily dossier proof signing |
| Signer wallet | One designated human | Sign regular certificate and document-proof transactions | Contract administration or role management |

The governance address can be retained in deployment/runbook configuration as a public address. Its private material is never placed in THV environment variables. The signer private key/seed phrase is never stored, requested, logged or transmitted by THV.

`blockchain.sign` is an application permission, separate from reviewer/council approval capabilities. Application RBAC decides who may link a wallet; the active verified-wallet rule decides who can see and sign the queue. On-chain `ISSUER_ROLE` is independently checked before THV returns a signing intent.
