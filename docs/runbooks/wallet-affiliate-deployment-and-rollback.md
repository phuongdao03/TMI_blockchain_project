# Wallet and Affiliate Deployment and Rollback

## Current release status

The backend includes the finance ledger, withdrawal review, a separately gated
payOS payout adapter, and Celery payout tasks. The wallet/admin withdrawal UI
exists. Affiliate backend APIs and commission processing remain pending; the
affiliate page is a UI shell without working server endpoints. Do not call the
feature set production-ready or enable money movement.

## Configuration defaults

The .env.example defaults include:

| Setting | Default | Current effect |
|---|---|---|
| WALLET_WITHDRAWAL_ENABLED | false | Must be true with DB withdrawal_enabled for new requests |
| PAYOUT_LIVE_ENABLED | false | Environment gate; worker requires it |
| Finance DB withdrawal_enabled | false | Independent request gate |
| Finance DB payout_live_enabled | false | Independent payout gate |
| PAYOS_PAYOUT_PROVIDER | disabled | Worker accepts payos only |
| PAYOS_PAYOUT_CLIENT_ID / API_KEY / CHECKSUM_KEY | empty | Separate payout credentials |
| AFFILIATE_ENABLED | false | Affiliate server module/routes pending |
| AFFILIATE_AUTO_CREATE_FOR_USERS | true | No backend affiliate code currently consumes it |
| AFFILIATE_EXCLUDED_ROLES | SUPER_ADMIN,MODERATOR | Intended policy; not currently consumed |
| AFFILIATE_ATTRIBUTION_WINDOW_DAYS | 30 | Intended policy; no server tracking path |
| COMMISSION_AUTO_APPROVAL | false | Commission workflow pending |
| AFFILIATE_DIRECT_COMMISSION_ENABLED | false | Commission workflow pending |
| AFFILIATE_LEVEL2_COMMISSION_ENABLED | false | Level-two path pending |
| AFFILIATE_COMMISSION_HOLD_DAYS | 30 | Commission workflow pending |

Payout worker calls require the payout environment flag, provider selection, all
three payout secrets, and the database payout setting. Withdrawal creation has
its own environment and database flags. Keep payout and encryption credentials
in the deployment secret store.

## Migration deployment

Review migrations 0153_finance_ledger.py, 0154_wallet_withdrawals.py, and
0155_finance_permissions.py against the release database and exact Alembic
head. Back up the database and exercise upgrades on a production-like copy.
From backend/, the standard command is:

    alembic upgrade head

Confirm finance tables, constraints (including the SENDING payout attempt
state), immutability triggers, singleton settings, and permission catalogue.
The supported-bank table has no provider-verified bank list seeded by these
migrations; populate it only from an approved source.

## Worker deployment and recovery

Run the Celery worker for payout tasks and Celery Beat for reconciliation.
The finance API dispatches process_queued_payouts immediately after an
authorized payout request. Beat polls known provider IDs every 60 seconds.
The periodic reconciliation task does not re-submit QUEUED attempts; verify
broker dispatch and monitor QUEUED/SENDING/UNKNOWN requests. An ambiguous
outcome without payout ID or a broker failure needs an operator/engineering
recovery path before live use.

## Safe rollback

1. Disable WALLET_WITHDRAWAL_ENABLED and PAYOUT_LIVE_ENABLED; set both finance
   database flags false. Keep PAYOS_PAYOUT_PROVIDER=disabled.
2. Preserve backups, request IDs, audits, withdrawal events, payout attempts,
   and finance history.
3. If migrations contain no financial/withdrawal history and permission codes
   are unassigned, review guarded downgrade behavior in an isolated copy.
4. If protected history exists, retain the tables and roll forward with a
   corrective migration. Migrations refuse destructive rollback when finance
   or withdrawal records exist; permission downgrade refuses assigned codes.
5. Verify existing service-wallet topups/payments and run internal
   reconciliation after recovery.

Do not truncate tables, remove immutability triggers by hand, or restore an old
application against a newer schema without compatibility review.

## Production activation gates

Require legal/tax/privacy approval, a validated identity process and bank
catalogue, approved commission source/rules, staffed independent approvals,
confirmed payOS payout enrollment/eligibility, monitoring, known/unknown
outcome recovery, reconciliation, backup, and rollback exercise. The
environment flags, provider credentials, and database settings are separate
gates. Affiliate APIs and commission processing are not ready.