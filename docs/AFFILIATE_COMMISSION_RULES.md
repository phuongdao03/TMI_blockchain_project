# Affiliate Commission Rules

## Status

No affiliate commission model, calculation service, review route, or
commission-credit event is implemented. `FinanceLedger` supports the
`COMMISSION_CREDIT` and `COMMISSION_REVERSAL` transaction types, but no current
production service calls them. The configured hold period defaults to 30 days;
direct commission, level two, and auto-approval default off. These flags are
not yet connected to an affiliate workflow.

## Rule approval record

Before any rate is enabled, an authorized policy owner must approve a versioned
rule containing:

- Eligible service and final settlement event.
- Commission basis (for example, the precise treatment of discounts, fees,
  taxes, cancellations, partial payments, and refunds).
- Rate or fixed amount, currency, maximum, and rounding rule in integer VND.
- Hold duration and the event from which the hold starts.
- Effective dates and treatment of conversions created under an older version.
- Exclusions, self-referral checks, reversal window, and dispute process.
- Approver, approval evidence, and audit reference.

Do not copy example percentages from a prompt into executable policy. Rates and
eligibility are business configuration and require explicit approval.

## Target lifecycle

1. A verified final service settlement creates one commission with a unique
   source reference and immutable calculation/rule snapshot.
2. The commission remains `PENDING`/`ON_HOLD` through the configured hold.
3. Once eligible, it becomes `READY_FOR_REVIEW`; a finance operator reviews
   source payment, attribution, rule version, refund status, and fraud signals.
4. Approval posts one balanced `COMMISSION_CREDIT` into
   `COMMISSION_AVAILABLE`. Rejection posts no user credit.
5. A confirmed refund or reversal uses a separate source record and an
   idempotent reversing journal. Never edit or delete the original commission.

Only service settlement events may qualify. Wallet topups are deposits, not a
service conversion. A payment order that is pending, cancelled, expired,
partially paid, or unresolved does not qualify. Source eligibility and partial
refund treatment remain pending business approval.

## Required safeguards

- Unique `(source payment, rule, affiliate)` attribution or an equivalent
  database constraint prevents duplicate commissions.
- A transactional outbox or equivalent ensures paid events are retried safely.
- Admin/reviewer and privileged accounts are excluded even with mixed roles.
- Commission approval is manual; the requester/beneficiary cannot approve their
  own commission.
- Pending, held, rejected, and reversed amounts never appear as available.
- Level two stays disabled until separately approved and legally reviewed.
