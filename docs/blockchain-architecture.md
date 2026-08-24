# THV blockchain architecture

THV keeps the business workflow in PostgreSQL. Polygon records only the immutable proof of a frozen dossier version or document evidence; it never receives PII, internal comments, storage URLs, files, email addresses, or passwords.

```text
Applicant → internal review/approval → frozen dossier version + canonical hash
          → blockchain transaction (CREATED) → human signer queue
          → wallet broadcast → receipt + confirmations + contract read-back
          → CONFIRMED → certificate/public verification
```

`BlockchainTransaction` is the durable record of the proof. In human mode, `CREATED` means waiting for a human signature, `SIGNING` has an unexpired intent, `BROADCAST` has a server-verified transaction hash, and `CONFIRMED` has passed receipt, confirmation and state checks. The dossier remains `ANCHOR_PENDING` until confirmation.

The existing `CertificateRegistry` remains authoritative for on-chain access control. It uses `ISSUER_ROLE`; THV does not rename or rewrite it merely to call it a verifier role. The governance wallet grants/revokes that role; the signer wallet holds only `ISSUER_ROLE`.

The backend creates all canonical payloads and contract calldata. The browser can only request an intent, pass it to an EIP-1193 wallet, and return the transaction hash. On receipt, THV checks sender, recipient, chain, zero value, calldata hash, receipt event, confirmation depth and contract read-back.
