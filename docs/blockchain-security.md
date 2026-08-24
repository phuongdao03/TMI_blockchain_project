# Blockchain security controls

- No signer private key, seed phrase or mnemonic is accepted by the UI, API, database or logs.
- Wallet ownership uses a random, one-time, short-lived EIP-191 challenge. The backend stores only a SHA-256 nonce digest and marks it consumed after success.
- Wallet addresses are checksummed before comparison. Exactly one active wallet link exists across THV.
- `blockchain.sign`, an active linked wallet, matching connected wallet, configured chain and on-chain `ISSUER_ROLE` are all required.
- The backend derives dossier proof, contract address and encoded call from frozen server state. It validates the callback transaction rather than trusting a client-supplied hash.
- Intents expire and a partial unique index permits one open intent per transaction. Revocation cancels open intents.
- Confirmation requires a successful receipt, expected contract/event, canonical block, required confirmations and state read-back. A mismatch is audited as `CHAIN_STATE_MISMATCH` and is never presented as verified.
- The worker can resume `BROADCAST` transactions after restart. It does not rebroadcast a client-submitted hash.
- Rate limits, CSRF protection and server-side RBAC apply to all mutation endpoints.

Security-sensitive operational changes—wallet rotation, role grant/revoke, pause/unpause and deployment—must be performed by the governance process, not by normal THV staff accounts.
