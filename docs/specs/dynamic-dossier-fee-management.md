# Dynamic dossier fee management

## Goal

Make dossier fees policy driven and reviewable. The fee shown to an applicant must come from one approved policy effective at the server's current UTC time. A fee is accepted and snapshotted only when the applicant confirms submission. Existing obligations and payment orders keep their recorded amounts.

## Requirements

- Use a versioned fee policy with fee type, dossier type scope, integer VND amount, half-open UTC effective interval, lifecycle state, creator, approver, and immutable approval history.
- A policy change is effective by time lookup; no restart, manual activation, or retroactive rewrite is needed. Only one approved policy can cover a given fee type/scope/time. Serialize concurrent publication and reject overlaps.
- Preview fee before submission. Re-resolve it in the submit transaction. If the policy/version changed after preview, return a conflict with the current quote and require the applicant to consent again.
- Do not create payment/fee obligations by opening a page or requesting a quote. Create one immutable obligation when a confirmed submission is accepted; snapshot fee type, policy/version, gross, waiver, due, and status.
- Reuse current wallet ledger, PayOS/payment idempotency, webhook verification, and reconciliation. Late/duplicate events must not debit twice. Never add an automatic surcharge.
- Waivers are explicit, reasoned, scoped to one dossier/fee, one use, and require a distinct approver. Existing financial capabilities remain separately authorized.
- Admin workspace exposes Transactions, Waivers & Exceptions, Policies, and Reconciliation. Use server pagination for transaction history.
- Define granular permissions for read, policy create/approve/cancel, obligation management, waiver request/approve, payment actions, and reconciliation. Audit every mutation.
- No production DB migration or real-money transaction is part of implementation.

## Boundaries

- Preserve existing payment, wallet, commission, nomination, and review behavior.
- Do not backfill a policy or assign a current amount to historical dossiers/obligations without authoritative evidence.
- A missing or ambiguous policy fails closed for new submission fees; retain already captured snapshots.
- Existing certificate/issuance and unrelated commerce fees keep their own fee types and behavior.

## Acceptance criteria

- Temporal resolution honors `starts_at <= now < ends_at`, including exact boundaries and UTC normalization.
- Concurrent overlapping approvals cannot both commit.
- A stale quote cannot submit at an unconfirmed price; a refreshed quote can be accepted.
- One submission retry, checkout retry, duplicate webhook, or late webhook cannot create a duplicate obligation or wallet debit.
- Waivers cannot be self-approved, reused, or applied outside their dossier/fee scope.
- Admin routes reject principals missing the exact capability; menu visibility follows those capabilities.
- Existing obligations are unchanged by migration and remain payable against their snapshots.
- Migration is additive and tested against isolated databases. No production migration is executed.

## Implementation plan

1. Extend billing persistence with fee policy lifecycle, scoped waivers, obligation snapshots, audit events, and concurrency-safe overlap checks. Add migration and migration tests.
2. Add policy quote/admin APIs and focused service tests for effective-time resolution, lifecycle, overlap, RBAC, and waiver approvals.
3. Rework submission confirmation to quote/recheck policy and persist one obligation/payment snapshot atomically; test idempotency, old snapshots, and stale quote handling.
4. Build the four-tab admin fee workspace and wire granular permission checks; add client/API tests.
5. Run focused backend/frontend tests, format/lint/type checks relevant to touched files, review diff, and document staging-only rollout.

## Known rollout constraint

No live application DB was inspected as part of this task. The former 5,000,000 VND environment fallback has been removed. The implementation does not seed a fee or claim any amount is current. Operations must configure and approve policy in staging before accepting submissions for a dossier type.
