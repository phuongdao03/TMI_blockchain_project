# Affiliate Architecture

## Implementation status

The local implementation includes affiliate profiles, referral click capture,
first-touch attribution, versioned commission rules, append-only commission
records, manual review, payout balances, API routes, and user/admin screens.
Migrations `0153` through `0156` are additive and have migration tests; they have
not been applied to a production database. Legal, identity, tax, bank-provider,
and live payout acceptance remain outstanding.

Ordinary `USER` accounts receive profiles automatically when active, including
email verification, Firebase signup, or applicant upgrade. If email signup
includes a referral, the pending account may receive a profile and locked
attribution at registration so the referral survives email verification.
Eligibility requires exactly the `USER` role and no employee record; mixed
staff/admin roles are excluded. Existing eligible users are backfilled with
deterministic referral codes. Admin profile suspension preserves the profile,
attribution, and history.

## Runtime flow

1. A referral link carries a code in the root `?ref=` query. The frontend records
   a deduplicated click ID and keeps the code/click ID for email registration or
   Firebase exchange. Applicant upgrade can claim a referral as a fallback.
2. The backend locks attribution by referred-user ID and accepts one referral
   within the published attribution window. The client cannot select an
   affiliate for a purchase.
3. Successful paid-service settlements call the affiliate service in the same
   database transaction. Eligible sources are dossier fee obligations,
   membership purchases, and advertising orders. Wallet top-ups, drafts, and
   order creation do not create commissions. Dossier billing's legacy
   `STANDARD` code maps to commission service code `DOSSIER_SUBMISSION`.
4. The record captures its source reference, service, source amount, rate, rule
   version, commission amount, earned time, and hold deadline. Unique source
   reference plus transaction boundaries prevent duplicate accrual.
5. Commissions begin `PENDING`. Finance must approve or reject each record.
   Approval credits available commission immediately when no hold remains;
   otherwise it moves to `ON_HOLD`. A scheduled worker releases only approved
   holds after maturity. Rejections and reversals retain the original record.
6. Available commission is held in a separate finance account and may fund a
   withdrawal. It never uses the prepaid service wallet.

```text
paid source event
  -> unique PENDING commission
  -> finance approve -> ON_HOLD (when hold remains)
  -> scheduled maturity release -> COMMISSION_AVAILABLE
  -> withdrawal reservation -> finance review -> separately queued payout
```

The valid commission states are `PENDING`, `ON_HOLD`, `AVAILABLE`, `REJECTED`,
`REVERSED`, and `SUPPRESSED`. Level two remains database-constrained to false
and zero. Rule version 1 is published but disabled with zero rates. Affiliate
and direct commission feature flags default off; approval is always manual.

## Financial and operational boundaries

- Finance transfers use immutable, balanced journal entries with unique
  idempotency/source keys. Available and reserved balances derive from postings.
- A withdrawal request reserves available commission and enters
  `PENDING_REVIEW`. Approval does not initiate a bank transfer. A separately
  authorized finance operator queues it for the gated worker.
- Bank account data is encrypted at rest and masked in owner responses. Full
  destination details are limited to finance permission and use `no-store`.
- Payout execution requires a database switch, environment switch, configured
  provider, and separate payOS payout credentials. All gates default closed.
  Tests use mock HTTP transport and make no transfer.
- A timeout or ambiguous payout outcome retains the reserve for reconciliation;
  the worker does not automatically create a second payout.
- A reversal from available commission debits the affiliate's pooled available
  account. It fails atomically when the remaining balance is insufficient; no
  debt or post-withdrawal recovery mechanism is implemented.
- A full refund event integration and partial-refund policy do not yet exist.
  Existing `REFUNDED` payment status alone does not reverse commissions.

## API and user interface

User routes expose a dashboard, click capture, authenticated referral claim,
privacy-safe referral aggregates, and commission history. Admin routes expose
profile search/detail/suspend/restore and aggregate referral history, versioned
rule management, and commission approve/reject/reverse operations. Referral
history omits referred-user email and user ID.

The frontend provides wallet withdrawal/bank account controls, affiliate link
sharing/history, and `/admin/affiliate` profile, referral, commission, and rule
workflows. Admin controls are permission-gated and require reasons for profile
status changes and commission rejection/reversal.

See [API contract](WALLET_AFFILIATE_API.md),
[attribution policy](AFFILIATE_ATTRIBUTION_POLICY.md),
[commission rules](AFFILIATE_COMMISSION_RULES.md),
[legal gates](AFFILIATE_LEGAL_COMPLIANCE.md), and the
[test report](WALLET_AFFILIATE_TEST_REPORT.md).
