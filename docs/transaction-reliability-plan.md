# Transaction reliability repair plan

## Findings

- The browser receives a wallet hash but keeps the selected proof in `SIGNING` while the submit API waits for an RPC transaction lookup. The backend also leaves a persisted hash in `SIGNING` if that lookup has not propagated.
- PayOS reconciliation can replace a confirmed `PAID` status with an older `PROCESSING` or `FAILED` response. The payment creation paths also call PayOS while holding database locks; a provider timeout can leave an external payment link without a local record.
- Existing proof reconciliation verifies receipt, event, confirmation depth and contract read-back; payment webhook signature and amount checks, durable workers and idempotency records already exist.

## Implemented slices

1. **Wallet hash visibility:** Reproduce the `SIGNING` state after a hash in frontend and backend tests. Move UI to `BROADCAST` immediately and persist that state when the backend receives the hash. Status GET reads the database without waiting for RPC; the worker performs on-chain reconciliation and stops periodic RPC lookups after `CONFIRMED`. Verify pending receipt, reload and no duplicate wallet prompt.
2. **Monotonic payment confirmation:** Guard provider reconciliation and late webhook events so a verified `PAID` order cannot regress, and terminal failed/cancelled/expired/refunded orders cannot reopen from stale snapshots. Record a verified late paid event against a terminal order as an audit conflict for manual review. Enqueue certificate issuance only on the transition to `PAID`.
3. **Checkout ambiguity:** Commit an order reservation before calling PayOS. Resolve an uncertain create response by the same `orderCode`; the worker and replay use that reservation. Provider creation, lookup, reconciliation and cancellation run outside database transactions.
4. **Bounded polling:** After five minutes the blockchain and payment screens stop automatic polling. Users can refresh status manually; reconciliation workers continue.
5. **Final verification:** Run focused and repository tests, lint, type checking and build; document deployment and rollback in the handoff.

No production transaction, refund or deployment is part of this work.

## Deployment and rollback

- Deploy the backend, Celery worker and frontend together. No migration, contract change, dependency or new environment variable is required. Confirm the existing Polygon RPC/chain/contract settings and PayOS API credentials, checksum key and callback URLs without displaying secrets.
- In a controlled environment, verify hash-before-receipt and confirmed on-chain proof, PayOS return before and after webhook, duplicate webhook, and a single certificate issuance. Watch the existing audit trail and worker errors for aged `BROADCAST` transactions, `PROCESSING` reservations without a provider ID, pending payments, provider mismatches and rejected webhooks.
- To roll back, pause new checkout and signing submissions, resolve missing `paymentLinkId` reservations by `orderCode` with the new worker or manual PayOS lookup, then revert application images together. Preserve payment/proof records and continue reconciliation. Do not create replacement links before matching the old `orderCode`.
- Production Polygon and PayOS behavior remains unverified. A provider `PAID` state for an already cancelled/expired local order requires manual investigation. No new metrics store or dashboard was added; use existing audit, worker logs and status queries.
