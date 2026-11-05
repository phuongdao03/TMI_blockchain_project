# Wallet, Withdrawal, and Affiliate API

All routes below use the /api/v1 prefix and the standard SuccessEnvelope.
Authenticated mutations use the session CSRF dependency. Topup and withdrawal
creation require an Idempotency-Key. Amounts are integer VND.

## Existing service wallet API

| Method and path | Purpose | Status |
|---|---|---|
| GET /wallet | Prepaid service balance, journal history, topups | Implemented; excludes commission |
| POST /wallet/topups | Start payOS collection topup | Implemented |
| POST /wallet/topups/{topup_id}/checkout | Resume topup checkout | Implemented |
| POST /wallet/topups/{topup_id}/reconcile | Reconcile collection order | Implemented |
| GET /wallet/topups/{topup_id}/qr | Read owner-scoped topup QR | Implemented |
| POST /payment-orders/{order_id}/wallet-payment | Pay service order from prepaid balance | Implemented |

## User bank and withdrawal API

| Method and path | Body/query | Behavior |
|---|---|---|
| GET /wallet/banks | — | List enabled supported bank BINs |
| GET /wallet/bank-accounts | — | Owner's accounts; number masked |
| POST /wallet/bank-accounts | { bank_bin, account_number, account_name, is_default? } | Encrypt/save owner-scoped account |
| PATCH /wallet/bank-accounts/{id}/default | — | Set owner-scoped default |
| DELETE /wallet/bank-accounts/{id} | — | Disable account without deleting history |
| GET /wallet/withdrawal-settings | — | Effective withdrawal flags, limits, fees |
| GET /wallet/withdrawals?limit=&offset= | — | List caller's requests |
| POST /wallet/withdrawals | { bank_account_id, amount_minor } plus idempotency header | Reserve available commission; create PENDING_REVIEW |
| GET /wallet/withdrawals/{id} | — | Read owner-scoped request |
| POST /wallet/withdrawals/{id}/cancel | — | Cancel pending-review request and release reserve |

The request path uses COMMISSION_AVAILABLE; it cannot withdraw
Wallet.balance_minor. The normal /wallet response has not been extended
with commission totals.

## Finance admin API

| Method and path | Required permission | Behavior |
|---|---|---|
| GET /admin/withdrawals?status=&limit=&offset= | finance.read | List requests |
| GET /admin/withdrawals/{id} | finance.read | Read review/event history, saved payout ID, and full destination |
| POST /admin/withdrawals/{id}/approve | finance.withdrawals.approve | Record approval; threshold may need a second actor |
| POST /admin/withdrawals/{id}/reject | finance.withdrawals.approve | Reject with { reason }; release reserve |
| POST /admin/withdrawals/{id}/payout | finance.payouts.execute | Create one attempt and dispatch worker after approval |
| POST /admin/withdrawals/{id}/verify-bank | finance.identity.verify | Record destination-bank evidence |
| POST /admin/finance/users/{user_id}/identity-verification | finance.identity.verify | Record identity status/evidence/reason |
| GET /admin/finance/settings | finance.settings.manage | Read limits, fees, and effective payout gate |
| PATCH /admin/finance/settings | finance.settings.manage | Update withdrawal/payout flags, limits, fees, threshold |
| POST /admin/finance/banks | finance.banks.manage | Add/update bank BIN and evidence URL |
| GET /admin/payouts/reconciliation | finance.read | Check internal journal and reserve totals |

GET /admin/withdrawals/{id} returns full destination details. Treat it as
sensitive financial data. Reconciliation is internal; it does not query payOS.
There is no dedicated payout-attempt resource; admin withdrawal detail includes event history and provider ID when recorded, but not the full PayoutAttempt record.

## Affiliate API

| Method and path | Required access | Behavior |
|---|---|---|
| GET /affiliate/me | Authenticated | Dashboard, referral link, commission totals, and available/reserved balances |
| POST /affiliate/referral-clicks | Public | Record referral code and event ID |
| POST /affiliate/referrals/claim | Authenticated + CSRF | Claim attribution for the signed-in user |
| GET /affiliate/me/referrals | Authenticated | List the caller's attributed referrals; supports limit/offset |
| GET /affiliate/me/commissions | Authenticated | List the caller's commissions; supports status/limit filters |
| GET /admin/affiliate/profiles | `affiliate.profiles.manage` | Search/filter and paginate affiliate profiles |
| GET /admin/affiliate/profiles/{user_id} | `affiliate.profiles.manage` | Read profile detail |
| GET /admin/affiliate/profiles/{user_id}/referrals | `affiliate.profiles.manage` | Read aggregate referral history without referred-user PII |
| GET /admin/affiliate/profiles/{user_id}/referrals | `affiliate.profiles.manage` | Read attributed referral dates and aggregate conversions/revenue/commission; no referred-user PII |
| POST /admin/affiliate/profiles/{user_id}/suspend | `affiliate.profiles.manage` + CSRF | Suspend a profile with a reason |
| POST /admin/affiliate/profiles/{user_id}/restore | `affiliate.profiles.manage` + CSRF | Restore a profile with a reason |
| GET/POST /admin/affiliate/commission-rules | `affiliate.rules.manage` | List/create versioned commission rules |
| POST /admin/affiliate/commission-rules/{rule_set_id}/publish | `affiliate.rules.manage` + CSRF | Publish a rule set |
| GET /admin/affiliate/commissions | `affiliate.commissions.approve` | Search/filter commission review queue |
| POST /admin/affiliate/commissions/{commission_id}/{action} | `affiliate.commissions.approve` + CSRF | `action` is `approve`, `reject`, or `reverse` |

Paths above omit the `/api/v1` prefix. Rule `service_code` values are matched
against the paid-service hook. For dossier billing, the legacy
`FeeObligation.service_code=STANDARD` is normalized to
`DOSSIER_SUBMISSION` before commission rule lookup. Membership and advertising
hooks use `MEMBERSHIP` and `ADVERTISING`; wallet topups do not create
commissions.

## Payout provider API (server-to-server)

The worker adapter calls payOS POST /v1/payouts and
GET /v1/payouts/{payoutId}. These are provider requests, not public
application routes. There is no payout callback or dedicated payout-attempt endpoint; admin withdrawal detail exposes event history and a saved provider ID. Provider-ID polling is worker-only.
