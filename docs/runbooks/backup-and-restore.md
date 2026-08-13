# Backup and restore

## Targets

- Database and critical certificate metadata: **RPO 24 hours**, **RTO 4 hours**.
- Contract deployment artifacts and Cloudinary inventory: **RPO 24 hours**,
  **RTO 8 hours**.
- Redis is operational state, not the source of business truth; queues are
  rebuilt or reconciled from durable records.

Neon automated backups/PITR remain the authoritative database recovery source.
Daily operational backup bundles contain certificate metadata, a Cloudinary
inventory and contract artifacts. They contain no wallet private key.

## Daily validation

1. Download the backup bundle to an isolated restore host.
2. Run `infrastructure/scripts/validate-backup.sh <directory>`; the bundle must
   contain `manifest.sha256`, `certificate-metadata.json`,
   `cloudinary-inventory.json` and `contract-artifacts.tar.gz`.
3. Run `infrastructure/scripts/check-backup-age.sh <backup-root> 26` from the
   backup scheduler. It validates the newest bundle and returns exit code 70
   when the newest valid bundle is older than 26 hours.
4. Confirm checksum, JSON parsing and contract archive checks all pass.
5. Record bundle timestamp, validator output and retention expiry without
   recording secrets.
6. The `backup_freshness` alert pages platform on-call when the age signal
   exceeds 93,600 seconds for 15 minutes.

## Quarterly restore drill

1. Open a change ticket and assign restore owner plus independent verifier.
2. Restore the selected Neon point into an isolated non-production project.
3. Apply the matching immutable application image and migration revision.
4. Import certificate metadata and compare counts, certificate numbers and
   canonical hashes.
5. Reconcile Cloudinary public IDs and verify a sample of signed private assets.
6. Load contract deployment artifacts and verify network, chain ID, address and
   ABI hash.
7. Run register/login, dossier read, certificate download and public
   verification smoke tests.
8. Measure achieved RPO/RTO, destroy the isolated environment and retain the
   sanitized report.

## Signed drill evidence

Record every PostgreSQL restore, Redis-loss and application rollback drill as a
strict JSON document. The approved schema accepts only:

- drill type, staging timestamps and `PASS`/`FAIL` status;
- target and achieved RPO/RTO in minutes;
- backup ID, manifest SHA-256, Alembic revision and immutable image tag;
- checksum, smoke-test and duplicate-side-effect results;
- the operational owner and independent verifier identifiers.

Do not add URLs, credentials, personal data, provider payloads or free-form
incident notes. Keep the Ed25519 private key in the approved secret manager and
provide it only as a restricted file on the signing host:

```bash
READINESS_EVIDENCE_PRIVATE_KEY_FILE=/run/secrets/readiness-evidence-ed25519 \
  node infrastructure/scripts/sign-readiness-evidence.mjs \
  restore-evidence.json restore-evidence.sig
```

The independent verifier retrieves the pinned public key from a separate trusted
location and verifies both schema gates and signature before attaching the
artifacts to the release ticket:

```bash
READINESS_EVIDENCE_PUBLIC_KEY_FILE=/etc/tmi/readiness-evidence-public.pem \
  node infrastructure/scripts/verify-readiness-evidence.mjs \
  restore-evidence.json restore-evidence.sig
```

A valid signature proves that the evidence file has not changed after signing;
it does not replace review of the restore environment, query plans or provider
records. Failed drills are also signed and retained.

## Redis-loss recovery drill

1. Use staging only; record the current release and durable pending counts.
2. Stop scheduler and workers, then replace Redis with an empty instance.
3. Confirm login rate limits, cache and queue state fail safely while Redis is
   unavailable.
4. Start Redis, scheduler and one worker per queue. Reconcile pending payments,
   blockchain transactions and outbox records from PostgreSQL.
5. Run login, dossier, payment-status and public-verification smoke tests.
6. Compare durable counts before/after, confirm no duplicate payment or
   certificate, and attach sanitized timestamps to the drill ticket.

The drill passes only when no durable business record depends on restored Redis
data and all replayed jobs remain idempotent.

## Local and CI failure regression

Run the deterministic database, Redis and blockchain RPC failure checks with:

```bash
node infrastructure/scripts/run-operational-readiness-regressions.mjs \
  --output operational-readiness-evidence
```

The JSON artifact and checksum are deliberately labelled `simulation_only`. They
prove application failure handling and are retained by CI for 14 days, but they
do not satisfy the quarterly staging restore or Redis-loss drill.

## Production restore decision

Production restore requires incident commander, database owner and business
owner approval. Freeze writes, capture a final forensic snapshot, document the
chosen recovery point, restore to a new database, validate it, then switch the
secret-store connection reference. Do not overwrite the damaged database.
