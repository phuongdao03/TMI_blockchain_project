# Private document encryption runbook

Private media is inspected and hashed before AES-256-GCM encryption. Only the
ciphertext object is retained after activation; authorized downloads are
decrypted by the backend and returned with `Cache-Control: private, no-store`.

## Configuration

- `MEDIA_PRIVATE_ENCRYPTION_ENABLED=true` is mandatory in production.
- `MEDIA_PRIVATE_ENCRYPTION_ACTIVE_KEY_ID` identifies the write key.
- `MEDIA_PRIVATE_ENCRYPTION_KEYS` is a JSON map of key IDs to base64-encoded
  32-byte keys. Inject it from managed secret storage; never commit actual values.
- Historical keys are decrypt-only once a different active ID is selected.

The service refuses production startup when encryption is disabled, the active
ID is missing or any key is malformed. Local development may keep encryption
disabled until a shared API/worker keyring is configured.

## Rotation

1. Generate 32 random bytes in approved managed key storage.
2. Add the new key under a unique ID while retaining all historical keys.
3. Deploy API and workers with the expanded keyring.
4. Change the active key ID and deploy again; new media now uses the new key.
5. Confirm old and new test documents both download and verify successfully.
6. Do not remove an old key until an audited migration proves no media row
   references its ID and backup/restore has been tested.

Never log the keyring, nonce/tag combination with ciphertext, decrypted bytes,
signed provider URLs or storage credentials.

## Failure handling

- Encryption/upload/delete failure leaves media quarantined and retryable.
- Retry after ciphertext persistence reuses the stored ciphertext and repeats
  idempotent plaintext deletion instead of generating another object.
- Invalid tag, hash or length blocks delivery/reverification.
- Deleting an encrypted media record targets its ciphertext object, not the
  already removed staging object.

## Legacy backfill

- Migration `0051_private_media_encryption` keeps recognized public-work media
  active and quarantines all legacy private media as `LEGACY_UNENCRYPTED`.
- The scheduled provenance backfill queues at most 25 legacy private rows per
  cycle through the same inspect, hash, encrypt and plaintext-delete workflow.
- Do not enable production traffic until the database reports zero private rows
  with `LEGACY_UNENCRYPTED`, `PENDING` or `FAILED` encryption status.
