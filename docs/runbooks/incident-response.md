# Incident response

## Severity and ownership

- **SEV-1:** security exposure, data-integrity risk, public verification down or
  payment corruption. Page incident commander, platform, security and business
  owner immediately.
- **SEV-2:** partial workflow outage, queue delay or material latency
  regression. Page platform owner during support hours and escalate if impact
  grows.
- **SEV-3:** degraded non-critical function with workaround. Create an owned
  ticket.

Never paste tokens, cookies, private keys, raw webhook bodies or personal
documents into chat, tickets or telemetry. Use request IDs and redacted audit
records.

## First 15 minutes

1. Acknowledge the alert and assign incident commander, operations lead and
   communications lead.
2. Record start time, release tag, affected flows and safe request IDs.
3. Check `/health`, `/ready`, error rate, P95 latency, DB pool and queue age.
4. Stop risky writes or disable the affected integration when data integrity is
   uncertain.
5. Rollback the application image when the incident correlates with a release.
6. Preserve logs and audit evidence; do not mutate failed payment or blockchain
   records manually.

## API errors

Compare 5xx endpoints by request ID, check dependency readiness and the latest
release. Roll back above twice baseline or when a new error type is sustained.

## Queue backlog

Check Redis health, worker heartbeat and oldest message age. Restart one worker
only after confirming tasks are idempotent. Scale workers gradually; never purge
the queue as a recovery shortcut.

## Database

Stop deploys, inspect Neon connections and long-running queries. Reduce worker
concurrency before increasing connection limits. Escalate to restore only after
confirming corruption or unrecoverable loss.

## Authentication

Compare failed-attempt rate by provider and request ID. Check Firebase status,
session signing health and rate-limit saturation. For a suspected credential
attack, page security, preserve redacted evidence and revoke affected sessions;
never weaken MFA or rate limits to restore access.

## Redis

Treat Redis as disposable operational state. Stop consumers before replacing an
unhealthy instance, start Redis empty, then resume scheduler and workers in
small batches. Reconcile pending payments, blockchain transactions and durable
outbox rows from PostgreSQL. Never restore an old queue snapshot or mark durable
work complete from Redis state.

## Payment webhook

Verify provider status and signature failures without logging raw payloads.
Reconcile through the service command/API; never mark orders paid directly in
the database.

## Certificate issuance

Pause certificate workers, inspect durable issuance and blockchain records, then
retry through the idempotent worker/API path after storage, signer and RPC
health are green. Do not upload a replacement PDF manually or issue a second
on-chain record for the same dossier.

## Blockchain

Check RPC availability, signer balance, nonce lock and pending transaction age.
Use idempotent reconciliation/retry paths. Never replace a signer key during an
active incident without the key-rotation procedure and dual approval.

For a chain-state mismatch, unexpected role or repeated revert, stop workers and
have the approved pauser call `pause()` from the administrator identity. Confirm
the pause on the explorer and preserve the transaction receipt. Resume only
after reconciliation matches the canonical block and the incident commander,
security owner and blockchain owner approve `unpause()`.

## Wallet balance

Confirm the expected network and wallet address, then fund through the approved
treasury process. Treat unexpected balance movement as SEV-1.

## Backup freshness

Run `infrastructure/scripts/check-backup-age.sh <backup-root> 26` on the
isolated operations host. Exit code 70 means the newest bundle is stale; exit
code 65 means no valid bundle was found or validation failed. Open a SEV-2
incident, preserve the last valid bundle, and repair the scheduler before
starting a restore drill. Do not copy secrets into the incident record.

## Alert routing rehearsal

Before a staging release and quarterly thereafter, send a bounded synthetic
event to the configured receiver. The receiver URL must use HTTPS and the token
must come from the secret manager; neither value belongs in the evidence file.

```bash
ALERT_TEST_WEBHOOK_URL=https://alerts.example/ingest \
ALERT_TEST_AUTH_TOKEN_FILE=/run/secrets/alert-probe-token \
ALERT_TEST_AUTH_TOKEN="$(< "$ALERT_TEST_AUTH_TOKEN_FILE")" \
  node infrastructure/scripts/probe-alert-delivery.mjs
```

Record the returned test ID, receiver-side event ID, route, received timestamp
and acknowledgement timestamp. Confirm the event is visibly marked synthetic and
does not page the production incident channel. A local HTTP receiver is allowed
only in automated tests with `ALERT_TEST_ALLOW_HTTP=1`.

Create a strict acknowledgement JSON containing only `schemaVersion`,
`environment`, `synthetic`, `testId`, `receiverEventId`, `route`, `sentAt`,
`receivedAt`, `acknowledgedAt`, `owner` and `status`. Retain its normalized copy
and checksum with:

```bash
node infrastructure/scripts/validate-alert-acknowledgement.mjs \
  alert-acknowledgement-input.json alert-acknowledgement-evidence
```

The validator accepts only staging synthetic events with chronological
timestamps and `ACKNOWLEDGED` status. The checksum proves file integrity; an
independent reviewer must still compare the event with the receiver record.

## Resolution

Verify critical user journeys, keep enhanced monitoring for one hour, publish a
sanitized incident summary and schedule a blameless review within two business
days. Track every corrective action with owner and due date.
