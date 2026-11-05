# Affiliate and Withdrawal Legal/Compliance Gates

## Status

This is an operational review checklist, not a legal conclusion. The repository
does not include an approved legal opinion, affiliate terms, tax treatment,
identity-verification provider, or production payout authorization. No feature
should be represented as legally cleared by this document.

## Required organization decisions

Before collecting referral data or enabling commission/payout operations, the
organization should obtain documented review from qualified Vietnam legal,
tax, privacy, and financial-compliance advisers for:

- Whether the proposed stored service balance and commission withdrawal model
  creates licensing or other regulated activity, and which funds may be held,
  spent, refunded, or paid out.
- Merchant/provider terms, payout account eligibility, supported categories,
  limits, destination-bank restrictions, and dispute/recall responsibilities.
- User identity checks, sanctions/fraud controls, evidence handling, access,
  retention, deletion, and incident response.
- Affiliate program terms, marketing/referral disclosures, prohibited conduct,
  cancellation/refund impacts, dispute handling, tax reporting, and required
  invoices/receipts.
- Consent and privacy notice for click/referral attribution, cookie/local
  storage, analytics, retention, and cross-device matching.
- Accounting treatment for commission liabilities, withheld/reversed amounts,
  provider fees, failed transfers, and reconciliation differences.

## Release checklist

- [ ] Legal memo identifies the allowed business model and prohibited flows.
- [ ] Terms and privacy notices are approved and published before collection.
- [ ] Tax and invoice/reporting responsibilities have named owners and process.
- [ ] Identity and bank verification methods, evidence, access, retention, and
  escalation are approved; the current operator-recorded checks are not an
  external verification service.
- [ ] payOS confirms payout account enablement, credentials, categories,
  destination banks, fees, limits, and support escalation.
- [ ] Independent approval and daily finance operations are staffed.
- [ ] Reconciliation, exception handling, backups, and rollback are exercised.
- [ ] A release owner signs off on enabling the relevant server-side flags.

The current safe defaults are withdrawals disabled, live payout disabled,
affiliate disabled, direct commission disabled, level two disabled, and
automatic commission approval disabled. Do not change these defaults based on
an incomplete checklist.
