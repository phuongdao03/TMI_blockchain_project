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

## Production restore decision

Production restore requires incident commander, database owner and business
owner approval. Freeze writes, capture a final forensic snapshot, document the
chosen recovery point, restore to a new database, validate it, then switch the
secret-store connection reference. Do not overwrite the damaged database.
