# Human signing flow

1. Internal approval freezes a `DossierVersion` and creates the deterministic
   proof.
2. The transaction is persisted as `CREATED`; no backend key is used in
   `BLOCKCHAIN_SIGNER_MODE=human`.
3. The designated THV user connects a wallet, asks THV for a one-time EIP-191
   challenge, and signs it in the wallet.
4. THV recovers the signing address, checks it against the requested address,
   then stores only its checksummed public address. One active signer wallet is
   enforced globally.
5. The signer queue is available only to the account holding the active verified
   link and `blockchain.sign` permission.
6. Before signing, THV revalidates the frozen proof, dossier state, wallet link,
   configured chain/contract, `ISSUER_ROLE`, gas estimate and balance; then it
   stores a short-lived intent.
7. MetaMask or another EIP-1193 wallet opens the transaction. The user, not THV,
   confirms broadcast.
8. THV independently retrieves the transaction, validates `from`, `to`, chain,
   zero value and calldata hash, then records it as `BROADCAST`.
9. A worker checks receipt/event/confirmations and reads the contract state back
   before `CONFIRMED`.
10. If the wallet broadcasts successfully but the browser loses the returned
    transaction hash, status reconciliation reads the exact on-chain proof,
    locates the uniquely indexed `ProofRecorded` event near its recorded
    timestamp, verifies its asset ID, hash, version, signer and canonical block,
    then restores the transaction as `BROADCAST` or `CONFIRMED`. The operator
    must not sign again.

Wallet rejection, wrong account, wrong chain, expired intent and malformed/fake
transaction hash all remain non-success states. The client never sends a proof
hash, contract address, calldata or final status.

The trust UI distinguishes storage from proof: the encrypted original remains in
THV storage, while Polygon stores its SHA-256 fingerprint, the authorized
organization wallet and an independently inspectable transaction. Any content
change produces a different fingerprint.
